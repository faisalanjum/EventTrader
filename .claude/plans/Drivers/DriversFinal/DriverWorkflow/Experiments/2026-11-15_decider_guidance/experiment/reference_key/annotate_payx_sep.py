from source_annotations import Reference
r=Reference('PAYX_2025-09-30T09.30');S=r.span;B=r.between;A=r.add
context=S('PR003','Let me now turn to our updated guidance for the year, which assumes the current macro environment. We are reaffirming our fiscal 2026 outlook with the exception of our earnings expectation, which we are raising.','annual period, macro assumption and movement')
common=dict(subject='Paychex, Inc.',period_text='fiscal 2026',company_confirmed=True,driver_state='reaffirmed')
pending=['Verify calendar and exact scope/measurement qualifiers from source; no legacy field defaults.']
cost=B('PR002','We are on track to achieve targeted PACOR revenue synergies and exceed our initial cost synergy expectations.','We are pursuing additional synergies beyond this target while retaining our flexibility to reinvest those gains for additional growth and innovation investments.','current cost-synergy target; pursuing further opportunities is not a stated higher amount')
A('P1-01','Paycor cost-synergy target',[cost],dict(**common,level_low='90',level_high='90',level_unit='m_usd',qualifier='approximately',measurement_words=['cost synergy'],business_scope='PACOR acquisition'),pending)
rows=[
 ('P1-02','Total revenue growth','Total revenue is still expected to grow between 16.5% and 18.5%.','16.5','18.5','unknown',None),
 ('P1-03','Revenue-synergy contribution to growth','And as we previously noted, we would expect revenue synergies to contribute 30 to 50 basis points of growth in fiscal 2026.','30','50','basis_points',None),
 ('P1-04','Management Solutions revenue growth','Management Solutions is expected to grow in the range of 20 to 22%.','20','22','unknown','Management Solutions'),
 ('P1-05','PEO and Insurance Solutions revenue growth','PEO and Insurance Solutions is expected to grow in the range of 6 to 8%.','6','8','unknown','PEO and Insurance Solutions'),
 ('P1-06','Interest on funds held for clients','Interest on funds held for clients is still expected to be in the range of $190 to $200 million.','190','200','m_usd',None),
 ('P1-07','Adjusted operating income margin','Adjusted operating income margin is expected to be approximately 43%.','43','43','percent',None),
 ('P1-08','Effective income tax rate','Our effective income tax rate is expected to be in the range of 24% to 25%.','24','25','percent',None)]
for i,name,text,lo,hi,unit,scope in rows:
 A(i,name,[context,S('PR003',text,'forecast quantity')],dict(**common,level_low=lo,level_high=hi,level_unit=unit,business_scope=scope,qualifier='approximately' if i=='P1-07' else None),pending)
eps=S('PR003','And as I mentioned, we are now raising our earnings expectations with adjusted diluted earnings per share now expected to grow between 9% and 11% up from 8.5% to 10.5% that we shared with you last quarter.','current and earlier forecasts with exact different roles')
A('P1-09','Adjusted diluted EPS growth',[context,eps],dict(**{**common,'driver_state':'raised'},level_low='9',level_high='11',level_unit='unknown',previous_forecast_values=['8.5','10.5'],measurement_words=['adjusted','diluted']),pending+['Earlier 8.5–10.5 is comparison evidence, not current guidance; do not calculate a revision amount.'])
q2=B('PR003','I\'ll provide you a little bit of color for the second quarter.','And, of course, this is based on our current assumptions, which are subject to change.','two Q2 guidance quantities and their lead-in')
A('P1-10','Q2 total revenue growth',[context,q2],dict(period_text='second quarter',level_low='18',level_high='18',level_unit='unknown',qualifier='approximately',driver_state='unknown',company_confirmed=True),pending+['Do not assume the blanket annual reaffirmation specifically establishes a Q2 movement.'])
A('P1-11','Q2 adjusted operating margin',[context,q2],dict(period_text='second quarter',level_low='41',level_high='41',level_unit='percent',qualifier='approximately',driver_state='unknown',company_confirmed=True),pending)
peo=S('PR003','And as previously noted, we expect revenue to accelerate in the back half of the year as we anniversary the at-risk revenue growth headwinds we experienced last fiscal year.','worded PEO/insurance growth outlook; stated cause is not automatically a condition')
peo2=S('QA002','we feel really good about where the PO is, and as you mentioned, we will, you know, anniversary those MPP headwinds, and we\'ll start seeing some stronger growth with the easier compare as we move into the back half of the year.','corroborating same-source PEO growth outlook')
A('P1-12','PEO growth accelerates in H2',[context,S('PR003',rows[3][2],'scope antecedent'),peo,peo2],dict(period_text='back half of the year',value_text='revenue to accelerate',company_confirmed=True),['Resolve exact PEO versus PEO-and-insurance scope; causal headwind comparison belongs in evidence, not automatically conditions.'])
paycor=B('QA001','Jared Levine [905]:','we would expect, you know, the business to grow double digits on a full-year basis.','management confirms double-digit recurring-revenue growth, not the analyst low-double-digit wording')
A('P1-13','Paycor recurring revenue growth',[paycor],dict(period_text='full-year basis',value_text='double-digit growth',level_unit='unknown',business_scope='pay core',measurement_words=['recurring revenue'],company_confirmed=True),pending+['Do not add low from analyst wording or infer a numeric range.'])
expense=B('QA003','Mark Marcon [1158]:','would probably be consistent with what we would see going forward.','reference to current organic expense growth as future outlook; source says four-year basis')
A('P1-14','Organic expense growth continues at current level',[expense],dict(printed_reference_value='3%',qualifier='probably closer to about',measurement_words=['strip it out','organically'],period_text=['four-year basis','going forward'],company_confirmed=True),['Do not silently repair four-year to full-year; determine supported horizon from question and answer.','Confirm the current 3% reference is adopted as the forecast, not merely an actual; source calls for continuation, not an exact unqualified point.'],status='claim_requires_association')
organic=B('QA005','But you saw an improvement in the organic growth of the overall business from a total revenue standpoint.','We knew that. That\'s how the plan was built.','company-wide organic revenue growth, not Management Solutions alone; distinguishes Q1 actual')
A('P1-15','Full-year company organic revenue growth',[organic],dict(period_text='full year',level_low='5',level_high='5',level_unit='unknown',measurement_words=['organic'],business_scope='overall business',company_confirmed=True),pending)
enrollment=B('QA008','We have enrollments in October.','So we\'re in very, very early days.','expected employee enrollment share at a stated future enrollment window')
A('P1-16','October enrollment share',[S('QA007',r.parts['QA007'],'analyst question split across stored exchanges'),S('QA008','in Florida with that plan?','question continuation'),enrollment],dict(printed_value='25%',qualifier='only about',period_text='October timeframe',company_confirmed=True),['Resolve population denominator and whether this is a forward operating forecast or fixed enrollment-cycle description.'],status='borderline_claim')
arpu=B('QA010','Michael Fontana [2206]:','So I\'m not looking at a big ARPU increase.','management narrows expected value from new partnership')
A('P1-17','Bill partnership ARPU outlook',[arpu],dict(value_text='not looking at a big ARPU increase',company_confirmed=True),['No explicit target horizon established here; do not create one from planned product-launch dates.'],status='source_insufficient_for_record')
shutdown=B('QA015','David (for Ashish Sabhadra) [2788]:','And so I don\'t expect any impact directly to our business.','company forecast of direct shutdown exposure; source lacks a precise metric/horizon')
A('P1-18','No direct government-shutdown impact expected',[shutdown],dict(value_text='no direct impact',company_confirmed=True),['Determine admissible standing metric and horizon; do not create a generic bucket or treat a policy question as quantified guidance.'],status='borderline_claim')
r.save({
 'PR000':'Operator introduction.', 'PR001':'Disclaimer, report/filing schedule, no specific financial forecast.',
 'PR002':'P1-01 cost-synergy target; actual performance, product plans and general opportunity statements separate.',
 'PR003':'P1-02–12, annual and Q2 guidance plus earlier EPS comparison; preceding results are actuals.',
 'PR004':'Question transition.', 'QA000':'Current demand/bookings, not future amounts.',
 'QA001':'P1-13; analyst low-double-digit wording not fully adopted.', 'QA002':'P1-12 supporting PEO outlook, actual performance and cause explanation.',
 'QA003':'P1-14 current-to-future expense reference; literal four-year wording cannot be silently corrected.',
 'QA004':'Current recurring growth reconciliation, integration and realized sale example, no new forecast amount.',
 'QA005':'P1-15; source explicitly says total company organic growth. Prior/current Q1 figures are not future guide.',
 'QA006':'Reasons for raised EPS; analyst 50-pips revision not independently confirmed as a numeric amount by management.',
 'QA007':'Question-only fragment continued in QA008.', 'QA008':'P1-16 plus repeated PEO H2 outlook; actual enrollment and operating plans separate.',
 'QA009':'Pricing/value strategy; no specific forecast.', 'QA010':'P1-17 and product-release plans; future release date does not supply ARPU target period.',
 'QA011':'Current mix/results.', 'QA012':'AI/productivity plans and general benefits, no specified financial forecast.',
 'QA013':'Question-only exchange answered in QA014.', 'QA014':'Current synergies/pipeline and potential opportunities; not a new supported level.',
 'QA015':'P1-18 borderline direct exposure forecast; macro expectations not automatically company financial guidance.',
 'QA016':'Actions already taken and opportunities for more savings; no new target beyond P1-01.',
 'QA017':'Retirement Q1 result and closing optimism, no new specific forecast.'})
