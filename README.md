# tracing_translator

This project aims to take timing information from multiple different types of logs/inputs and consolidates information into a JSON file that can be opened and visualized with Chromium Tracing UI. Different input sources are aligned on the same timeline to visualize concurrency and sequence.

## Usage

### Requirements

The dependencies required by the project can be installed with pip:

```bash
python3 -m pip install -r requirements.txt
```

### Configuration

To use this utility, you must first define a config YAML (e.g. cfg.yml). 

#### Example

```yaml
inputs:
  - description: 'OneDNN Details'
    file_name: 'onednn.log'
    delimiter: ','
    header: 'onednn_verbose,timestamp,,operation,engine,primitive,implementation,prop_kind,memory_descriptors,attributes,auxiliary,problem_desc,exec_time'
    timing_format: 
      type: 'start_dur_combined'
      field_name: 'primitive'
      event_name: 'exec_time'
      ts_name: 'timestamp'
      arg_fields:
       - problem_desc
       - prop_kind
       - memory_descriptors
       - attributes
      ts_multiplier: 1e3
    pid: 1
    tid: 0
    regex_list:
      - 'onednn_verbose,\s*\d+\.\d+'
    removable_prefix: 'unwanted prefix'
  - description: 'Pytorch Trace'
    file_name: 'torchprof.json'
    timing_format:
      type: 'json_trace_pass_thru'
    pid: 1
    tid: 1
  - description: 'Other'
    file_name: 'layer_stats.log'
    delimiter: ','
    header: 'field,event,ts'
    timing_format:
      type: 'start_end_separate'
      field_name: 'field'
      event_name: 'event'
      ts_name: 'ts'
    pid: 2
    tid: 2
output_name: 'out.json'
```

#### Input Types

| Name | Description |
|---|---|
| `start_dur_combined` | Log file where the start timestamp and the duration are included on the same time | 
| `start_end_separate` | Log file where the start timestamp is on one line and the end timestamp is on another |
| `json_trace_pass_tru` | JSON file that is already viewable in the Chromium Tracing UI | 

#### Attributes To Assist Log File Processing

| Name | Description | 
|---|---|
| `header` | Comma separated string identifying the components present in the entries of the log file |
| `field_name` | Reflects the name of the operation |
| `event_name` | Reflects where to find the event name (Could be start/stop events or a duration entry) |
| `ts_name` | Reflects where to find the name of the timestamp |
| `arg_fields` | Additional operation details |
| `ts_multiplier` | Value to multiply the timestamp value to get everything on the same time scale |
| `regex_list` | Regular expression(s) to isolate entries in input log file where relevant data is present |

### Running The Utility

```bash
python main.py -c cfg.yml
```

#### Outputs

Will output `out.json` which you can view with a trace viewer (e.g. `chrome://tracing`, https://ui.perfetto.dev/)