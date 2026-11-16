from source_annotations import Reference
r=Reference('CTAS_2025-12-18T10.00'); S=r.span; B=r.between; A=r.add
lead=S('PR002','Turning to guidance, we are raising our fiscal 2026 financial guidance.','period and movement')
rev=S('PR002','We expect our revenue to be in the range of $11.15 billion to $11.22 billion, a total growth rate of 7.8% to 8.5%.','level and growth are distinct quantities')
eps=S('PR002','We expect diluted EPS to be in the range of $4.81 to $4.88, a growth rate of 9.3% to 10.9%.','diluted EPS level and growth')
ass=B('PR004','Earlier, Todd provided our updated guidance for the remainder of the fiscal year.','and the guidance does not include the impact of any future share buybacks or significant economic disruptions or downturns.','shared assumptions, explicit tax/interest forecasts, and nonrecurring prior asset-sale comparison')
tariff=S('QA004','The guide does contemplate the current environment for tariffs.','stated guidance assumption')
common=dict(subject='Cintas Corporation', period_text='fiscal 2026', period_scope='annual', driver_state='raised', company_confirmed=True)
pending=['Verify subject fiscal-calendar normalization.','Associate each applicable assumption/measurement qualifier with the correct forecast; do not copy all numbers as conditions.']
for i,name,span,lo,hi,unit,words in [
 ('DEC01','Revenue level',rev,'11150','11220','m_usd',[]),
 ('DEC02','Revenue growth',rev,'7.8','8.5','unknown',['growth rate']),
 ('DEC03','Diluted EPS level',eps,'4.81','4.88','usd',['diluted']),
 ('DEC04','Diluted EPS growth',eps,'9.3','10.9','unknown',['diluted','growth rate'])]:
 A(i,name,[lead,span,ass,tariff],dict(**common,level_low=lo,level_high=hi,level_unit=unit,value_shape='range',measurement_words=words),pending)
A('DEC05','Net interest expense',[ass],dict(period_text='fiscal 2026',level_low='104',level_high='104',level_unit='m_usd',qualifier='approximately',driver_state='unknown',company_confirmed=True),['Calendar normalization; preserve net and approximation.'])
A('DEC06','Effective tax rate',[ass],dict(period_text='fiscal 2026',level_low='20',level_high='20',level_unit='percent',comparison_text='which is the same compared to our fiscal 2025',driver_state='unknown',company_confirmed=True),['Calendar normalization; prior-year rate is not automatically previous guidance.'])
standing=S('QA001','So our target of mid to high single-digit organic growth is important to us, and we have so many different ways to grow that it gives us flexibility.','worded standing organic-growth target')
future=B('QA018','But, you know, whether it\'s the first half of the year or our guide for the second half,','we have a lot of confidence in that we can sustain that level of growth moving forward.','separate remaining-year and moving-forward horizons; reference back to growth algorithm')
A('DEC07','Standing organic growth target',[standing,future],dict(value_text='mid to high single-digit',measurement_words=['organic'],period_text='moving forward',level_unit='unknown',company_confirmed=True),['Establish which growth framing the later statement confirms; retain current H2 and undefined future horizons separately if both established.'])
ma=B('QA002','Andrew Steinerman [1076]:','So call it, you know, 30 to 35 bids.','analyst identifies second-half revenue contribution; management forecast with ambiguous transcript unit')
A('DEC08','Acquisition contribution to second-half revenue growth',[ma],dict(period_text='second half of the year',printed_values=['30','35'],printed_unit='bids',earlier_actual='70 bps',condition='no new acquisitions',company_confirmed=True),['Do not silently correct bids to basis points; determine whether the explicit earlier 70 bps comparison supports the unit.','Do not calculate half of 70 as a new forecast or substitute the current actual.'])
inc=B('QA003','Jim Rosakis [1335]:','and we think that\'s a great spot for us to run the business.','standing target, current actuals and two distinct guided periods')
A('DEC09','Standing incremental-margin target',[inc],dict(level_low='25',level_high='35',level_unit='percent',measure_text='incremental margin',company_confirmed=True),['Exact margin definition and explicit period/horizon must be resolved; analyst longer-term wording is not alone company confirmation.'])
A('DEC10','Annual incremental margin excluding prior asset gain',[inc],dict(level_low='29',level_high='30',level_unit='percent',period_text='this fiscal year',measurement_words=['when you adjust for the $15 million asset sale from last fiscal year'],company_confirmed=True),['Verify margin meaning and calendar.','The $15 million adjustment defines the comparison, not a new current forecast value or an unrelated condition.'])
A('DEC11','Second-half incremental margin',[inc],dict(level_low='30',level_high='33',level_unit='percent',period_text='back half of the year',company_confirmed=True),['Verify margin meaning and calendar; determine applicability of the prior-asset-sale adjustment.'])
fa=B('QA005','Todd Schneider [1608]:','So that\'s great.','first-aid growth outlook; preserve attribution and horizon')
A('DEC12','First-aid revenue growth outlook',[fa],dict(value_text='low double-digit',period_text='foreseeable future',level_unit='unknown',business_scope='first aid',company_confirmed=True),['Horizon mapping must not default to long-term; determine permitted undefined horizon.','Source quantity is growth, not a percentage level; no numeric conversion of worded amount.'])
mid=B('QA010','George Tong [2072]:','midpoint of 8.2.','explicit management midpoint of previously stated revenue-growth range')
A('DEC13','Explicit revenue-growth midpoint',[mid],dict(level_low='8.2',level_high='8.2',level_unit='unknown',qualifier='midpoint',period_text='full year',company_confirmed=True),['This midpoint is printed by management, not computed by extractor. Decide its representation with the same forecast range (DEC02), rather than automatically inventing a second independent forecast.'],status='claim_requires_representation')
qlead=S('QA011','and then as a follow-up can you just refresh us on the timing of the sap uh fire implementation costs are you expect are you still expecting','analyst question begins in the preceding stored exchange')
erp=B('QA012','Jason Haas [2315]:','and we\'re quite optimistic about the coming years.','question continuation and current/future rollout costs')
A('DEC14','Greater future fire ERP costs',[qlead,erp],dict(value_text='there is more cost to come in the future',business_scope='fire',company_confirmed=True),['Management confirms more future costs; do not assume it confirms every analyst proposed timing/margin detail.','Stored Q&A boundary splits the question; full source must remain available.'])
erp27=B('QA012','Scott Garula [2438]:','100 basis points for the fire protection business.','management quantified future ERP margin impact')
A('DEC15','Fire ERP rollout margin impact',[qlead,erp,erp27],dict(printed_values=['100'],level_unit='basis_points',qualifier='around',period_text='fiscal year 27',business_scope='fire protection',company_confirmed=True),['Resolve exact margin measure and negative headwind meaning from complete question and answer; do not infer positive growth from unsigned 100.','Verify fiscal dates.'])
buy=B('QA016','So I wouldn\'t just simply model in that we are going to lever up and be highly aggressive on buybacks.','We\'ll continue to look at that opportunistically and return that back to our shareholders as appropriate.','capital-allocation policy continuity, not a stated buyback amount')
A('DEC16','Buyback approach remains opportunistic',[buy],dict(company_confirmed=True,value_text='I wouldn\'t expect a change to our approach there.'),['Adjudicate forecast of a policy level versus general strategy; do not create quantified buyback or leverage guidance.'],status='borderline_claim')
A('DEC17','Remaining-half growth outlook',[standing,future],dict(value_text='mid to high single-digit growth',period_text='second half',company_confirmed=True),['Confirm organic versus total definition from full source, and current fiscal dates; no source comparison basis may be invented.'],status='claim_requires_association')
r.save({
 'PR000':'Operator introduction; no guidance.', 'PR001':'Participants and cautionary disclaimer; no specific forecast.',
 'PR002':'DEC01–04; earlier numbers are actual results.', 'PR003':'Reported segment performance, strategy and transition to guidance assumptions.',
 'PR004':'DEC05–06, shared assumptions and prior asset gain that will not recur; actual capital allocation not guidance.',
 'PR005':'General future commitment, no separate specific metric forecast.', 'PR006':'Question procedure.', 'PR007':'Operator procedure.',
 'QA000':'Observed employment/customer environment; no new specific forecast.',
 'QA001':'DEC07 standing organic-growth target; rest business examples. End includes next analyst introduction/question fragment.',
 'QA002':'DEC08; actual second-quarter contribution distinct from forecast.', 'QA003':'DEC09–11; actual incremental margins and comparison numbers must remain separate.',
 'QA004':'Tariff assumption applies to guide; sourcing statistics actual.', 'QA005':'DEC12; margin mix discussion is context, not a new quantified target.',
 'QA006':'Competition/current pricing and customer statistics.', 'QA007':'Actual capital deployment and uncertain acquisition pipeline, not a promised amount.',
 'QA008':'Closing greeting.', 'QA009':'Current sales/customer conditions.',
 'QA010':'DEC13 explicit midpoint/repeated annual range; generic expected leverage context.',
 'QA011':'Tariff response/current pricing; final words begin the question continued in QA012.',
 'QA012':'DEC14–15; rollout schedule itself is a planned act, financial cost/margin forecast distinct; actual acquisition contribution not future value.',
 'QA013':'Technology investment plans/general optimism, not a specified financial level.',
 'QA014':'Pricing strategy/current level and intent to improve efficiency, no definite amount/period forecast.',
 'QA015':'Current customer behavior.', 'QA016':'DEC16 policy-continuity borderline; analyst forecast of buybacks is not management guidance.',
 'QA017':'Actual segment shares and business examples.', 'QA018':'DEC07/17 standing and second-half growth outlook; generic geographic plans separate.',
 'QA019':'Closing and next release schedule, not financial guidance.'})
