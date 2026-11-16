import json,sys
sys.path.insert(0,'/tmp/decider_claude_review_20261115')
import main_path_trial as T
r=json.loads((T.R/'numeric_bounds_compact_request_prepared.json').read_text())
T.run('numeric_bounds_compact',r['state'],r['questions'],targets=r['targets'],note=r['note'])
