import yaml
import argparse
import json
from ProfileType import ProfileType

def load_config(cfg):
    with open(cfg, 'r') as f:
        return yaml.safe_load(f)
    
def generate_json(profile_types, output_fname):
    outdict = {"traceEvents": []}
    
    for pt in profile_types:
        for e in pt.create_entries():
            outdict['traceEvents'].append(e)

    with open(output_fname, 'w') as f:
        json.dump(outdict, f, indent=2)

def main():
    cfg = load_config(args.config)
    profile_types = []
    for c in cfg['inputs']:
        profile_types.append(ProfileType(c))

    generate_json(profile_types, cfg.get('output_name', 'out.json'))
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True, help="Configuration YAML file", dest="config")
    args = parser.parse_args()
    main()