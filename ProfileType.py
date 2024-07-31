from utils import generate_detailed_entry, generate_thread_name_entry
import pandas as pd
from io import StringIO

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
        self.log_data_df = self.prepare_input_data()
        self.log_data_df.columns = self.cfg.get('header').strip().split(',')

        self.log_data_to_dict()
    
    def prepare_input_data(self):
        with open(self.file_name, 'r') as f:
            input_data = f.readlines()

        filtered_data = []
        for l in input_data:
            if all(regex in l for regex in self.regex_list):
                filtered_data.append(l)

        try:
            df = pd.read_csv(StringIO(''.join(filtered_data)), delimiter=self.delimiter, header=None)
        except pd.errors.EmptyDataError as e:
            print('No matches found')
            exit()
        
        return df

class StartEndSeparate(_ProfileType):
    def log_data_to_dict(self):
        
        timing_fmt = self.cfg.get('timing_format')
        for index, row in self.log_data_df.iterrows():
            field = row[timing_fmt.get('field_name')]
            event = row[timing_fmt.get('event_name')]
            ts = float(row[timing_fmt.get('ts_name')])
            ts_multiplier = float(timing_fmt.get('ts_multiplier', 1.0))

            self.min_ts = min(self.min_ts, ts)
            self.max_ts = max(self.max_ts, ts)

            if field not in self.stat_dict.keys():
                self.stat_dict[field] = [[], []]

            if event == 'start':
                self.stat_dict[field][0].append(ts * ts_multiplier)
            else:
                self.stat_dict[field][1].append(ts * ts_multiplier)
    
    def create_entries(self):
        entries = []

        for l in self.stat_dict.keys():
            for idx in range(len(self.stat_dict[l][0])):
                start = self.stat_dict[l][0][idx]
                end   = self.stat_dict[l][1][idx]
                entries.append( 
                    generate_detailed_entry(ph="X", cat="cpu_op", name=l, pid=self.pid, tid=self.tid, 
                                            ts=start, dur=(end - start), args=None)
                )
                
        entries.append(generate_thread_name_entry(self.min_ts, self.pid, self.tid, self.description))

        return entries

class ProfileType():
    def __init__(self, cfg):
        if cfg.get('timing_format') is not None and cfg.get('timing_format').get('type') == "start_end_separate":
            self.instance = StartEndSeparate(cfg)

    def __getattr__(self, name):
        # assume it is implemented by self.instance
        return self.instance.__getattribute__(name)