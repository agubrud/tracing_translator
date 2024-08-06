from utils import generate_detailed_entry, generate_thread_name_entry
import pandas as pd
from io import StringIO
import json
import re

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
        self.log_data = self.prepare_input_data()
    
    def prepare_input_data(self):
        with open(self.file_name, 'r') as f:
            input_data = f.readlines()

        filtered_data = []
        for l in input_data:
            if all(re.search(regex, l) for regex in self.regex_list):
                filtered_data.append(l)

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

        """
        for index, row in self.log_data.iterrows():
            field = row[timing_fmt.get('field_name')]
            event = row[timing_fmt.get('event_name')]
            ts = float(row[timing_fmt.get('ts_name')])
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
        """
    
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

        """
        for index, row in self.log_data.iterrows():
            field = row[timing_fmt.get('field_name')]
            event = float(row[timing_fmt.get('event_name')])
            ts = float(row[timing_fmt.get('ts_name')])
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
                    argdict[e] = row[e]
            else:
                argdict = None

            self.stat_dict[field]['args'].append(argdict)
        """
    
class JSONTracePassThru(_ProfileType):
    def __init__(self, cfg):
        super().__init__(cfg)

        self.create_entries()

    def prepare_input_data(self):
        with open(self.file_name, 'r') as f:
            input_data = json.load(f)

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