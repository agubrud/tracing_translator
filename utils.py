def generate_detailed_entry(ph, cat, name, pid, tid, ts, dur, args):
        entry = {
        "ph": ph,
        "cat": cat, 
        "name": name, 
        "pid": pid, 
        "tid": tid,
        "ts": ts, 
        "dur": dur,
        "args": args
        }
        return entry

def generate_thread_name_entry(ts, pid, tid, label):
    entry = {
    "name": "thread_name", "ph": "M", "ts": ts, "pid": pid, "tid": tid,
    "args": {
      "name": f"{label}"
    }
    }
    return entry
    
def generate_entry(ph, name, s, pid, tid, ts, args):
    entry = {
    "name": name, 
    "ph": ph,
    "s": s,
    "pid": pid, 
    "tid": tid,
    "ts": ts
    }
    if args is not None:
        entry['args'] = args
    return entry