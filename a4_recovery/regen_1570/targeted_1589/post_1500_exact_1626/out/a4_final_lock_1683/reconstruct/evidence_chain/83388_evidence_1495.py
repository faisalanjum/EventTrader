p="/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/evidence_1495.py"
s=open(p).read()
s=s.replace('        extra = ("; " + "; ".join(d)) if d else "; every field identical"\n',
            '        extra = "; no field comparison, one side abstained" if (ab1 or ab2) else (("; " + "; ".join(d)) if d else "; every field identical")\n')
open(p,"w").write(s)
