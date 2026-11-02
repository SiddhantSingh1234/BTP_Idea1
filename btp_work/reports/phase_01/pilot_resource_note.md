# Pilot resource-monitor correction

The first four pilot records under `pilot_v1` observed the Windows venv redirector
only (roughly 4-5 MiB), rather than measuring the full interpreter process tree.
Those memory values are not accepted as compiler memory measurements. Their
raw records are retained. The two 30-second timeout records describe the
controller's observation; no claim of full descendant-termination coverage is
made for that initial monitor. A later filtered process inspection found no
matching remaining pilot workers.

Before the full campaign, the controller was changed to enumerate only descendants
of its own launched worker, monitor their combined memory, and explicitly terminate
all opened handles in that owned family at a cap. It never targets unrelated
processes. The measured quantity is the maximum observed sum of individual
process-family peak working sets, sampled every 0.2 seconds. This is labelled
as a monitored process-family upper bound, not an allocation-proof hard limit
or an isolated compiler-only RSS figure. A short second pilot validates this
path before the full batch. No compiler algorithm or source file was changed.
