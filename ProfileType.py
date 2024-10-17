from utils import generate_detailed_entry, generate_thread_name_entry
import pandas as pd
from io import StringIO
import json
import re
import math
import numpy as np

class _ProfileType():
    def __init__(self, cfg):
        self.cfg = cfg
        self.file_name = cfg.get('file_name')
        self.description = cfg.get('description', 'stats')
        self.delimiter = cfg.get('delimiter', ',')
        self.pid = cfg.get('pid', 0)
        self.tid = cfg.get('tid', 0)
        self.stat_dict = dict()
        self.min_ts = float('inf')
        self.max_ts = 0
        self.regex_list = cfg.get('regex_list', [])
        self.removable_prefix = cfg.get('removable_prefix', '')
        self.log_data = self.prepare_input_data()
    
    def prepare_input_data(self):
        with open(self.file_name, 'r') as f:
            input_data = f.readlines()

        filtered_data = []
        for l in input_data:
            if all(re.search(regex, l) for regex in self.regex_list):
                filtered_data.append(l.replace(self.removable_prefix, ''))

        try:
            df = pd.read_csv(StringIO(''.join(filtered_data)), delimiter=self.delimiter, header=None)
        except pd.errors.EmptyDataError as e:
            print('No matches found')
            exit()
        
        return df
    
    def create_entries(self):
        entries = []

        for l in self.stat_dict.keys():
            for idx in range(len(self.stat_dict[l]['ts'][0])):
                start = self.stat_dict[l]['ts'][0][idx]
                end   = self.stat_dict[l]['ts'][1][idx]
                args = self.stat_dict[l]['args'][idx]
                entries.append( 
                    generate_detailed_entry(ph="X", cat="cpu_op", name=l, pid=self.pid, tid=self.tid, 
                                            ts=start, dur=(end - start), args=args)
                )
                
        entries.append(generate_thread_name_entry(self.min_ts, self.pid, self.tid, self.description))

        return entries

class StartEndSeparate(_ProfileType):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.log_data.columns = self.cfg.get('header').strip().split(',')
        self.log_data_to_dict()
        
    def log_data_to_dict(self):
        
        timing_fmt = self.cfg.get('timing_format')

        header_idxs = {}
        for i,e in enumerate(self.log_data.columns.values):
            header_idxs[e] = i

        for row in self.log_data.values:
            field = row[header_idxs.get(timing_fmt.get('field_name'))]
            event = row[header_idxs.get(timing_fmt.get('event_name'))]
            ts = row[header_idxs.get(timing_fmt.get('ts_name'))]
            ts_multiplier = float(timing_fmt.get('ts_multiplier', 1.0))

            self.min_ts = min(self.min_ts, ts)
            self.max_ts = max(self.max_ts, ts)

            if field not in self.stat_dict.keys():
                self.stat_dict[field] = {'args': [], 'ts': [[], []]}

            if event == 'start':
                self.stat_dict[field]['ts'][0].append(ts * ts_multiplier)
            else:
                self.stat_dict[field]['ts'][1].append(ts * ts_multiplier)

            self.stat_dict[field]['args'].append(dict())
    
class StartDurCombined(_ProfileType):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.log_data.columns = self.cfg.get('header').strip().split(',')
        self.log_data_to_dict()

    def log_data_to_dict(self):
        
        timing_fmt = self.cfg.get('timing_format')

        header_idxs = {}
        for i,e in enumerate(self.log_data.columns.values):
            header_idxs[e] = i

        for row in self.log_data.values:
            field = row[header_idxs.get(timing_fmt.get('field_name'))]
            event = row[header_idxs.get(timing_fmt.get('event_name'))]
            ts = row[header_idxs.get(timing_fmt.get('ts_name'))]

            ts_multiplier = float(timing_fmt.get('ts_multiplier', 1.0))

            self.min_ts = min(self.min_ts, ts)
            self.max_ts = max(self.max_ts, ts)

            if field not in self.stat_dict.keys():
                self.stat_dict[field] = {'args': [], 'ts': [[], []]}

            self.stat_dict[field]['ts'][0].append(ts * ts_multiplier)
            self.stat_dict[field]['ts'][1].append((ts + event) * ts_multiplier)

            if timing_fmt.get('arg_fields') is not None:
                argdict = dict()
                for e in timing_fmt.get('arg_fields'):
                    argdict[e] = row[header_idxs.get(e)]
            else:
                argdict = None

            self.stat_dict[field]['args'].append(argdict)
    
class JSONTracePassThru(_ProfileType):
    def __init__(self, cfg):
        super().__init__(cfg)

        self.create_entries()
    
    def enhance_input_data(self, input_data):
        dt_lookup = {'float': 4}
        for e in input_data['traceEvents']:
            if 'aten::conv2d' in e.get('name').lower():
                input_dims = e.get('args').get('Input Dims')[0]
                wt_dims = e.get('args').get('Input Dims')[1]

                val_lists = []
                for idx, val in enumerate(e.get('args').get('Input type')):
                    if val == "ScalarList":
                        val_lists.append(eval(e.get('args').get('Concrete Inputs')[idx]))

                padding = val_lists[1]
                stride = val_lists[0]
                dilation = val_lists[2]

                out_x = math.floor((input_dims[-2] + (2 * padding[0]) - (dilation[0] * (wt_dims[-2] - 1))-1)/stride[0] + 1)
                out_y = math.floor((input_dims[-1] + (2 * padding[1]) - (dilation[1] * (wt_dims[-1] - 1))-1)/stride[1] + 1)
                output_dims = [input_dims[0], wt_dims[0], out_x, out_y]

                mac_count = input_dims[0] * (input_dims[1] * wt_dims[-2] * wt_dims[-1] * out_x * out_y) * wt_dims[0]
                op_count = mac_count * 2

                wt_dtype = dt_lookup[e.get('args').get('Input type')[1]]
                time_s = (e.get('dur')/1e6)
                e['args']['wt_mem_bw_gbps'] = int(np.prod(wt_dims))*wt_dtype/time_s/1e9
                e['args']['ops'] = op_count
                e['args']['effective_gops'] = op_count/time_s/1e9
            if 'aten::linear' in e.get('name').lower():
                input_dims = e.get('args').get('Input Dims')[0]
                wt_dims = e.get('args').get('Input Dims')[1]

                mac_count = input_dims[0] * input_dims[1] * wt_dims[0]
                op_count = mac_count * 2

                wt_dtype = dt_lookup[e.get('args').get('Input type')[1]]
                time_s = (e.get('dur')/1e6)
                e['args']['wt_mem_bw_gbps'] = int(np.prod(wt_dims))*wt_dtype/time_s/1e9
                e['args']['ops'] = op_count
                e['args']['effective_gops'] = op_count/time_s/1e9


    def prepare_input_data(self):
        with open(self.file_name, 'r') as f:
            input_data = json.load(f)
        self.enhance_input_data(input_data)
        return input_data['traceEvents']
    
    def create_entries(self):
        return self.log_data


class ProfileType():
    def __init__(self, cfg):
        if cfg.get('timing_format') is not None and cfg.get('timing_format').get('type') == "start_end_separate":
            self.instance = StartEndSeparate(cfg)
        elif cfg.get('timing_format') is not None and cfg.get('timing_format').get('type') == "start_dur_combined":
            self.instance = StartDurCombined(cfg)
        elif cfg.get('timing_format') is not None and cfg.get('timing_format').get('type') == "json_trace_pass_thru":
            self.instance = JSONTracePassThru(cfg)

    def __getattr__(self, name):
        # assume it is implemented by self.instance
        return self.instance.__getattribute__(name)