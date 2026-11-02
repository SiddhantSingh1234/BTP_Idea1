"""
Visualization Generator for Quantum Compiler Results
Generates circuit diagrams, movement animations, and heatmaps for all benchmarked circuits.
"""

import os
import re
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np
from qiskit import QuantumCircuit
from qiskit.visualization import circuit_drawer


class BulkVisualizationGenerator:
    """Generates all visualizations for multiple circuits in organized folders."""
    
    def __init__(self, instructions_dir='instruction_logs', output_base_dir='visualization_outputs'):
        self.instructions_dir = instructions_dir
        self.output_base_dir = output_base_dir
        self.R = 15  # Grid rows
        self.C = 15  # Grid cols
        
        # Create output directories
        os.makedirs(output_base_dir, exist_ok=True)
        self.circuits_dir = os.path.join(output_base_dir, 'circuits')
        self.movements_dir = os.path.join(output_base_dir, 'movements')
        self.heatmaps_dir = os.path.join(output_base_dir, 'heatmaps')
        self.animations_dir = os.path.join(output_base_dir, 'animations')
        
        for d in [self.circuits_dir, self.movements_dir, self.heatmaps_dir, self.animations_dir]:
            os.makedirs(d, exist_ok=True)
    
    def process_all_circuits(self, qasm_folder):
        """Process all circuits and generate visualizations."""
        if not os.path.isdir(self.instructions_dir):
            print(f"[ERROR] Instructions directory '{self.instructions_dir}' not found!")
            return

        instruction_files = sorted([f for f in os.listdir(self.instructions_dir) if f.endswith('_instructions.txt')])

        if not instruction_files:
            print(f"[ERROR] No instruction files found in '{self.instructions_dir}'")
            return

        print(f"Found {len(instruction_files)} instruction files to process...\n")
        
        for instruction_file in instruction_files:
            circuit_name = instruction_file.replace('_instructions.txt', '')
            print(f"Processing: {circuit_name}")
            
            # Load instructions
            instruction_path = os.path.join(self.instructions_dir, instruction_file)
            with open(instruction_path, 'r') as f:
                instructions = f.read().split('\n')
            
            # Generate circuit diagram
            qasm_path = os.path.join(qasm_folder, f"{circuit_name}.qasm")
            if os.path.exists(qasm_path):
                self.generate_circuit_diagram(qasm_path, circuit_name)
            
            # Generate movement visualizations
            viz = QubitMovementVisualizer(instructions, self.R, self.C)
            viz.parse_instructions()
            
            if viz.states:
                # Static movement plot
                static_path = os.path.join(self.movements_dir, f"{circuit_name}_movement.png")
                viz.create_static_plot(static_path)
                
                # Heatmap
                heatmap_path = os.path.join(self.heatmaps_dir, f"{circuit_name}_heatmap.png")
                viz.create_movement_heatmap(heatmap_path)
                
                # Animated GIF
                gif_path = os.path.join(self.animations_dir, f"{circuit_name}_animation.gif")
                viz.create_animated_gif(gif_path)
                
                print(f"  [OK] Generated all visualizations for {circuit_name}\n")
            else:
                print(f"  [WARN] No movement states found for {circuit_name}\n")

        print(f"\n[DONE] All visualizations saved to '{self.output_base_dir}/' directory")
        self.generate_summary_report()
    
    def generate_circuit_diagram(self, qasm_path, circuit_name):
        """Generate a proper circuit diagram using Qiskit."""
        try:
            circuit = QuantumCircuit.from_qasm_file(qasm_path)
            
            # Generate circuit diagram using matplotlib backend
            output_path = os.path.join(self.circuits_dir, f"{circuit_name}_circuit.png")
            circuit_drawer(circuit, output='mpl', filename=output_path, scale=0.7, fold=20)
            
            print(f"  [OK] Circuit diagram saved")
        except Exception as e:
            print(f"  [WARN] Could not generate circuit diagram: {e}")
    
    def generate_summary_report(self):
        """Generate a summary HTML report linking all visualizations."""
        html_path = os.path.join(self.output_base_dir, 'visualization_index.html')
        
        circuits = sorted([f.replace('_circuit.png', '') for f in os.listdir(self.circuits_dir) 
                          if f.endswith('_circuit.png')])
        
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Quantum Compiler Visualization Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .circuit-section { 
            background: white; 
            padding: 20px; 
            margin: 20px 0; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        img { 
            max-width: 100%; 
            border: 1px solid #ddd; 
            border-radius: 4px; 
            margin: 10px 0;
        }
        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .viz-item {
            background: #fafafa;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
        }
        .viz-item h3 { margin-top: 0; color: #4CAF50; }
    </style>
</head>
<body>
    <h1>Quantum Compiler Visualization Report</h1>
    <p><strong>Total Circuits Processed:</strong> """ + str(len(circuits)) + """</p>
"""
        
        for circuit_name in circuits:
            html_content += f"""
    <div class="circuit-section">
        <h2>{circuit_name}</h2>
        
        <h3>Circuit Diagram</h3>
        <img src="circuits/{circuit_name}_circuit.png" alt="{circuit_name} circuit">
        
        <div class="grid-container">
            <div class="viz-item">
                <h3>Qubit Movement</h3>
                <img src="movements/{circuit_name}_movement.png" alt="{circuit_name} movement">
            </div>
            
            <div class="viz-item">
                <h3>Occupancy Heatmap</h3>
                <img src="heatmaps/{circuit_name}_heatmap.png" alt="{circuit_name} heatmap">
            </div>
        </div>
        
        <div class="viz-item">
            <h3>Animated Qubit Movement</h3>
            <img src="animations/{circuit_name}_animation.gif" alt="{circuit_name} animation">
        </div>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[OK] HTML summary report saved to: {html_path}")


class QubitMovementVisualizer:
    """Parses hardware instructions and generates movement visualizations."""
    
    def __init__(self, hardware_instructions, R=15, C=15):
        self.instructions = hardware_instructions
        self.states = []
        self.R = R
        self.C = C
    
    def parse_instructions(self):
        """Extract qubit positions and actions at each timestamp."""
        current_positions = {}
        current_timestamp = None
        current_layout_slots = []  # Store layout slots for current timestamp
        
        for instruction in self.instructions:
            # Detect timestamp
            timestamp_match = re.search(r'--- Processing (.*?) ---', instruction)
            if timestamp_match:
                current_timestamp = timestamp_match.group(1)
                current_layout_slots = []  # Reset layout for new timestamp
                continue
            
            # Detect layout slots
            layout_match = re.search(r'\[LAYOUT_SLOTS: (.+)\]', instruction)
            if layout_match:
                slots_str = layout_match.group(1)
                # Parse format: "r1,c1-r2,c2;r3,c3-r4,c4;..."
                for slot_str in slots_str.split(';'):
                    if slot_str:
                        p1_str, p2_str = slot_str.split('-')
                        r1, c1 = map(float, p1_str.split(','))
                        r2, c2 = map(float, p2_str.split(','))
                        current_layout_slots.append(((r1, c1), (r2, c2)))
                continue
            
            # Detect initial placements
            initial_match = re.search(r'PLACE (?:active|idle) qubit (\d+) at position \(([\d.]+), ([\d.]+)\)', instruction)
            if initial_match:
                qubit = int(initial_match.group(1))
                r, c = float(initial_match.group(2)), float(initial_match.group(3))
                current_positions[qubit] = (r, c)
                continue
            
            # Detect shuttling moves
            shuttle_match = re.search(r'SHUTTLE qubit (\d+) from \(([\d.]+), ([\d.]+)\) to \(([\d.]+), ([\d.]+)\)', instruction)
            if shuttle_match:
                qubit = int(shuttle_match.group(1))
                r_new, c_new = float(shuttle_match.group(4)), float(shuttle_match.group(5))
                current_positions[qubit] = (r_new, c_new)
                continue
            
            # Detect CZ gates
            cz_match = re.search(r'CZ q\[(\d+)\], q\[(\d+)\] \(at locations \(([\d.]+), ([\d.]+)\), \(([\d.]+), ([\d.]+)\)\)', instruction)
            if cz_match and current_timestamp:
                q1, q2 = int(cz_match.group(1)), int(cz_match.group(2))
                
                if not self.states or self.states[-1]['timestamp'] != current_timestamp:
                    self.states.append({
                        'timestamp': current_timestamp,
                        'positions': dict(current_positions),
                        'active_pairs': [],
                        'layout_slots': list(current_layout_slots)  # Store layout
                    })
                
                self.states[-1]['active_pairs'].append((q1, q2))
        
        return self.states
    
    def create_static_plot(self, output_path):
        """Generate a grid of snapshots showing qubit positions."""
        if len(self.states) == 0:
            return
        
        cols = 4
        rows = (len(self.states) + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(16, 4*rows))
        if rows * cols == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        for idx, state in enumerate(self.states):
            ax = axes[idx]
            ax.set_xlim(-0.5, self.C - 0.5)
            ax.set_ylim(-0.5, self.R - 0.5)
            ax.set_aspect('equal')
            ax.set_title(f"{state['timestamp']}", fontsize=10, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_xticks(range(self.C))
            ax.set_yticks(range(self.R))
            
            # Draw layout slots as grey rectangles
            if 'layout_slots' in state:
                for (r1, c1), (r2, c2) in state['layout_slots']:
                    # Calculate rectangle dimensions (slightly larger than unit cell)
                    mid_r, mid_c = (r1 + r2) / 2, (c1 + c2) / 2
                    width = abs(c2 - c1) + 0.6
                    height = abs(r2 - r1) + 0.6
                    rect = mpatches.Rectangle((mid_c - width/2, mid_r - height/2), width, height,
                                             linewidth=1, edgecolor='grey', facecolor='lightgrey',
                                             alpha=0.3, zorder=0)
                    ax.add_patch(rect)
            
            positions = state['positions']
            for qubit, (r, c) in positions.items():
                ax.scatter(c, r, s=100, c='lightblue', edgecolors='black', linewidths=1, zorder=2)
                ax.text(c, r, str(qubit), ha='center', va='center', fontsize=8, zorder=3)
            
            for q1, q2 in state['active_pairs']:
                if q1 in positions and q2 in positions:
                    r1, c1 = positions[q1]
                    r2, c2 = positions[q2]
                    ax.plot([c1, c2], [r1, r2], 'r-', linewidth=2, alpha=0.6, zorder=1)
                    ax.scatter(c1, r1, s=150, c='red', edgecolors='darkred', linewidths=2, zorder=4)
                    ax.scatter(c2, r2, s=150, c='red', edgecolors='darkred', linewidths=2, zorder=4)
                    # Add qubit numbers to red (active) qubits
                    ax.text(c1, r1, str(q1), ha='center', va='center', fontsize=8, fontweight='bold', color='white', zorder=5)
                    ax.text(c2, r2, str(q2), ha='center', va='center', fontsize=8, fontweight='bold', color='white', zorder=5)
        
        for idx in range(len(self.states), len(axes)):
            axes[idx].axis('off')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_animated_gif(self, output_path, duration_per_frame=1000):
        """Generate an animated GIF showing qubit movement."""
        if len(self.states) == 0:
            return
        
        fig, ax = plt.subplots(figsize=(10, 10))
        
        def update(frame):
            ax.clear()
            state = self.states[frame]
            
            ax.set_xlim(-0.5, self.C - 0.5)
            ax.set_ylim(-0.5, self.R - 0.5)
            ax.set_aspect('equal')
            ax.set_title(f"Timestamp: {state['timestamp']}", fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_xticks(range(self.C))
            ax.set_yticks(range(self.R))
            ax.set_xlabel('Column', fontsize=12)
            ax.set_ylabel('Row', fontsize=12)
            
            # Draw layout slots as grey rectangles
            if 'layout_slots' in state:
                for (r1, c1), (r2, c2) in state['layout_slots']:
                    # Calculate rectangle dimensions (slightly larger than unit cell)
                    mid_r, mid_c = (r1 + r2) / 2, (c1 + c2) / 2
                    width = abs(c2 - c1) + 0.8
                    height = abs(r2 - r1) + 0.8
                    rect = mpatches.Rectangle((mid_c - width/2, mid_r - height/2), width, height,
                                             linewidth=1.5, edgecolor='grey', facecolor='lightgrey',
                                             alpha=0.3, zorder=0)
                    ax.add_patch(rect)
            
            positions = state['positions']
            for qubit, (r, c) in positions.items():
                ax.scatter(c, r, s=200, c='lightblue', edgecolors='black', linewidths=1.5, zorder=2)
                ax.text(c, r, str(qubit), ha='center', va='center', fontsize=10, fontweight='bold', zorder=3)
            
            for q1, q2 in state['active_pairs']:
                if q1 in positions and q2 in positions:
                    r1, c1 = positions[q1]
                    r2, c2 = positions[q2]
                    ax.plot([c1, c2], [r1, r2], 'r-', linewidth=3, alpha=0.7, zorder=1)
                    ax.scatter(c1, r1, s=250, c='red', edgecolors='darkred', linewidths=2.5, zorder=4)
                    ax.scatter(c2, r2, s=250, c='red', edgecolors='darkred', linewidths=2.5, zorder=4)
                    # Add qubit numbers to red (active) qubits
                    ax.text(c1, r1, str(q1), ha='center', va='center', fontsize=10, fontweight='bold', color='white', zorder=5)
                    ax.text(c2, r2, str(q2), ha='center', va='center', fontsize=10, fontweight='bold', color='white', zorder=5)
            
            idle_patch = mpatches.Patch(color='lightblue', label='Idle Qubits')
            active_patch = mpatches.Patch(color='red', label='Active Gates')
            ax.legend(handles=[idle_patch, active_patch], loc='upper right')
        
        anim = FuncAnimation(fig, update, frames=len(self.states), interval=duration_per_frame, repeat=True)
        writer = PillowWriter(fps=1)
        anim.save(output_path, writer=writer)
        plt.close()
    
    def create_movement_heatmap(self, output_path):
        """Generate a heatmap showing grid position usage frequency."""
        occupancy = np.zeros((self.R, self.C))
        
        for state in self.states:
            for qubit, (r, c) in state['positions'].items():
                occupancy[int(r), int(c)] += 1
        
        fig, ax = plt.subplots(figsize=(10, 10))
        im = ax.imshow(occupancy, cmap='hot', interpolation='nearest', origin='lower')
        ax.set_title('Qubit Occupancy Heatmap', fontsize=14, fontweight='bold')
        ax.set_xlabel('Column', fontsize=12)
        ax.set_ylabel('Row', fontsize=12)
        ax.set_xticks(range(self.C))
        ax.set_yticks(range(self.R))
        
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Number of Times Position Used', rotation=270, labelpad=20)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate visualizations for all benchmarked circuits")
    parser.add_argument('--qasm-folder', type=str, 
                       default='../dasatom/DasAtom-main/Data/qiskit-bench/qft/qft_small',
                       help='Path to folder containing QASM files')
    parser.add_argument('--instructions-dir', type=str, default='instruction_logs',
                       help='Directory containing instruction log files')
    parser.add_argument('--output-dir', type=str, default='visualization_outputs',
                       help='Base directory for visualization outputs')
    
    args = parser.parse_args()
    
    print("="*70)
    print("  QUANTUM COMPILER VISUALIZATION GENERATOR")
    print("="*70 + "\n")
    
    generator = BulkVisualizationGenerator(
        instructions_dir=args.instructions_dir,
        output_base_dir=args.output_dir
    )
    
    generator.process_all_circuits(args.qasm_folder)
    
    print("\n" + "="*70)
    print("  [DONE] VISUALIZATION GENERATION COMPLETE")
    print("="*70)
