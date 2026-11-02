"""Recover paper references from printed Table II and Figure 4 PDF vector paths."""
import argparse,csv,hashlib,json,math,re,statistics,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'.research-tools/python/Lib/site-packages'))
from pypdf import PdfReader,__version__ as PYPDF_VERSION
from pypdf.generic import ContentStream


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def normal(s):return re.sub('[^a-z0-9]','',s.lower())
def calibration(points):
    xs=[p[0] for p in points];ys=[p[1] for p in points];mx=statistics.mean(xs);my=statistics.mean(ys)
    slope=sum((x-mx)*(y-my) for x,y in points)/sum((x-mx)**2 for x in xs)
    intercept=my-slope*mx
    residual=max(abs(slope*x+intercept-y) for x,y in points)
    assert residual < max(1e-7,max(map(abs,ys))*1e-8),(points,residual)
    return slope,intercept,residual


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Use a new output under btp_work')
    pdf=ROOT.parent/'Papers/Priyanshu_Aditya_ISVLSI2026_AK_O.pdf'
    plan=json.loads((ROOT/'configs/studies/paper_focus_v2.json').read_text())
    assert digest(pdf)==plan['paper_pdf_sha256']
    reader=PdfReader(str(pdf));page=reader.pages[5]
    ledger=list(csv.DictReader((ROOT/'reports/phase_01/published_targets.csv').open()))
    wanted={normal(r['circuit']):r['circuit'] for r in ledger if r['family']=='tableII'}
    printed={};number=re.compile(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?')
    for line in page.extract_text(extraction_mode='layout').splitlines():
        matches=list(number.finditer(line))
        if len(matches)<12:continue
        tail=matches[-12:];key=normal(line[:tail[0].start()])
        if key in wanted:printed[wanted[key]]=[x.group() for x in tail]
    assert len(printed)==15,len(printed)
    references={}
    for case,values in printed.items():
        for offset,(grid,algorithm) in enumerate([(11,'dasatom'),(11,'rft'),(35,'dasatom'),(35,'rft')]):
            original=next(r for r in ledger if r['family']=='tableII' and r['circuit']==case and int(r['grid'])==grid and r['method']==('dasatom' if algorithm=='dasatom' else 'rft_paper_unknown_variant'))
            for name,index in [('compile_seconds',offset),('fidelity',offset+4),('movement_batches',offset+8)]:
                assert float(original[name])==float(values[index]),(case,grid,algorithm,name)
            references[('tableII',case,grid,algorithm)]={'family':'tableII','case':case,'grid':grid,'algorithm':algorithm,
                'paper_compile_seconds':float(values[offset]),'paper_runtime_us':None,
                'paper_fidelity':float(values[offset+4]),'paper_fidelity_literal':values[offset+4],
                'paper_movement_batches':int(values[offset+8]),'source_kind':'printed_Table_II',
                'source_page':6,'source_object':None,'compile_abs_uncertainty':.0005,'runtime_abs_uncertainty':None,
                'fidelity_log10_uncertainty':None,'movement_abs_uncertainty':0}
    colors=[(0.1215686275,0.4666666667,0.7058823529),(1.,0.4980392157,0.0549019608),
            (0.1725490196,0.6274509804,0.1725490196),(0.8392156863,0.1529411765,0.1568627451),
            (0.5803921569,0.4039215686,0.7411764706),(0.5490196078,0.337254902,0.2941176471)]
    identities=[('dasatom',11),('dasatom',20),('dasatom',35),('rft',11),('rft',20),('rft',35)]
    forms=[('/Im2','paper_compile_seconds'),('/Im3','paper_runtime_us'),('/Im4','paper_movement_batches'),('/Im5','paper_fidelity')]
    evidence={}
    for form_name,metric in forms:
        obj=page['/Resources']['/XObject'][form_name].get_object();ops=ContentStream(obj,reader).operations
        curves=[];ticks=[];path=[];color=None
        for i,(args,op) in enumerate(ops):
            if op==b'RG':color=tuple(float(v) for v in args)
            elif op==b'G':color=(float(args[0]),)*3
            elif op==b'm':path=[tuple(float(v) for v in args)]
            elif op==b'l':path.append(tuple(float(v) for v in args))
            elif op in [b'n',b'f',b'B']:path=[]
            elif op==b'S':
                if len(path)==12 and all(path[k+1][0]>path[k][0] for k in range(11)):
                    index=min(range(6),key=lambda j:sum((color[k]-colors[j][k])**2 for k in range(3)))
                    assert max(abs(color[k]-colors[index][k]) for k in range(3))<1e-8
                    curves.append((index,path[:]))
                elif len(path)==2 and abs(path[0][1]-path[1][1])<1e-8 and abs(path[0][0]-path[1][0])>800:
                    texts=[]
                    for a,o in ops[i+1:i+26]:
                        if o==b'TJ':texts.append(''.join(str(x) for x in a[0] if isinstance(x,str)))
                        elif o==b'Tj':texts.append(str(a[0]))
                    if metric!='paper_fidelity' and texts and re.fullmatch(r'\d+',texts[0]):ticks.append((path[0][1],float(texts[0])))
                    elif metric=='paper_fidelity' and texts[:2]==['1','0']:ticks.append((path[0][1],None))
                path=[]
        assert len(curves)==6 and {x[0] for x in curves}==set(range(6)),(form_name,len(curves))
        if metric=='paper_fidelity':
            assert len(ticks)==6
            # Exponents independently checked against the rendered logarithmic axis.
            ticks=list(zip(sorted(y for y,v in ticks),[-11.,-9.,-7.,-5.,-3.,-1.]))
        slope,intercept,residual=calibration(ticks)
        evidence[form_name]={'metric':metric,'ticks':ticks,'axis_scale':'log10' if metric=='paper_fidelity' else 'linear',
            'slope':slope,'intercept':intercept,'max_tick_fit_residual':residual,
            'stream_sha256':hashlib.sha256(obj.get_data()).hexdigest(),'curves':[]}
        for index,points in curves:
            algorithm,grid=identities[index];spacing=(points[-1][0]-points[0][0])/11
            assert max(abs(points[k][0]-(points[0][0]+k*spacing)) for k in range(12))<2e-6
            values=[]
            for k,(x,y) in enumerate(points):
                value=slope*y+intercept
                if metric=='paper_fidelity':value=10**value
                if metric=='paper_movement_batches':
                    assert abs(value-round(value))<1e-3,value
                    value=int(round(value))
                assert value>=0
                key=('fig4_qft','qft_'+str(5*(k+1)),grid,algorithm)
                row=references.setdefault(key,{'family':'fig4_qft','case':key[1],'grid':grid,'algorithm':algorithm,
                    'source_kind':'Figure_4_PDF_vector_reconstruction_not_author_raw_data','source_page':6,
                    'source_object':'/Im2-/Im5','paper_fidelity_literal':None,
                    'compile_abs_uncertainty':1e-5,'runtime_abs_uncertainty':.01,
                    'fidelity_log10_uncertainty':1e-6,'movement_abs_uncertainty':.001})
                row[metric]=value;values.append(value)
            evidence[form_name]['curves'].append({'algorithm':algorithm,'grid':grid,'color':list(colors[index]),'points':points,'values':values})
    assert len(references)==132 and sum(r['family']=='fig4_qft' for r in references.values())==72
    out.mkdir(parents=True)
    rows=sorted(references.values(),key=lambda r:(r['family'],r['case'],r['grid'],r['algorithm']))
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (out/'paper_reference.csv').open('w',newline='',encoding='utf-8') as handle:
        w=csv.DictWriter(handle,fieldnames=fields);w.writeheader();w.writerows(rows)
    dump(out/'vector_evidence.json',evidence)
    dump(out/'verification.json',{'checked_utc':datetime.now(timezone.utc).isoformat(),'pdf_sha256':digest(pdf),
        'paper_pdf':str(pdf),'page':6,'pypdf_version':PYPDF_VERSION,'table_configurations':60,
        'printed_numeric_cells_verified':180,'figure_configurations':72,'figure_metric_values_recovered':288,
        'vector_coordinates_are_not_author_raw_measurements':True,
        'uncertainty_policy':'Conservative coordinate/calibration floors: 1e-5 s, .01 us, .001 movement count, 1e-6 log10(F); printed TableII rounding kept separately',
        'caption_compilation_log_scale_matches_actual_axis':False,'actual_compilation_axis':'linear',
        'plot_color_legend_and_fidelity_exponents':'Checked against local page6.png rendering',
        'reference_sha256':digest(out/'paper_reference.csv')})
    print(json.dumps({'references':len(rows),'printed_cells_verified':180,'vector_metric_values':288}))
    for row in rows:
        if row['case']=='qft_60':print(json.dumps(row))


if __name__=='__main__':main()
