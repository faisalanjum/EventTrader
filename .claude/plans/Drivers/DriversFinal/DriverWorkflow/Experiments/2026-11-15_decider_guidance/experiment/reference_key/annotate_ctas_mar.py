from source_annotations import Reference
r=Reference('CTAS_2026-03-25T10.00');S=r.span;B=r.between;A=r.add
lead=S('PR002','Turning to guidance, we are raising our fiscal 2026 financial guidance.','annual period and movement')
rev=S('PR002','We expect our revenue to be in the range of $11.21 billion to $11.24 billion, a total growth rate of 8.4% to 8.7%.','revenue level and growth')
eps=S('PR002','We expect adjusted diluted EPS to be in the range of $4.86 to $4.90, a growth rate of 10.5% to 11.4%.','adjusted diluted EPS level and growth')
eps_ex=S('PR002','The adjusted EPS guide does not include the impact of non-recurring transaction expenses related to Unifirst.','EPS measurement exclusion, not a separate assumption')
ass=B('PR004','Earlier, Todd provided our updated guidance for the remainder of the fiscal year.','and the guide does not include the impact of any future share buybacks or significant economic disruptions or downturns.','annual guidance assumptions with separate interest/tax forecasts')
fuel=B('QA003','Scott Garula [1108]:','an increased level of gas prices at the pump into our guidance.','energy assumption, no stated 30% assumption here')
common=dict(subject='Cintas Corporation',period_text='fiscal 2026',driver_state='raised',company_confirmed=True)
pending=['Verify calendar and applicability of all shared assumptions; keep measurement exclusions separate from assumptions.']
for i,name,sp,lo,hi,u,q in [
 ('MAR01','Annual revenue level',rev,'11210','11240','m_usd',[]),
 ('MAR02','Annual revenue growth',rev,'8.4','8.7','unknown',['growth rate']),
 ('MAR03','Annual adjusted diluted EPS',eps,'4.86','4.90','usd',['adjusted','diluted']),
 ('MAR04','Annual adjusted diluted EPS growth',eps,'10.5','11.4','unknown',['adjusted','diluted','growth rate'])]:
 A(i,name,[lead,sp,ass,fuel]+([eps_ex] if i in ['MAR03','MAR04'] else []),dict(**common,level_low=lo,level_high=hi,level_unit=u,measurement_words=q),pending)
A('MAR05','Annual net interest expense',[ass],dict(period_text='fiscal 2026',level_low='101',level_high='101',level_unit='m_usd',qualifier='approximately',company_confirmed=True),['Calendar; preserve net and approximation.'])
A('MAR06','Annual effective tax rate',[ass],dict(period_text='fiscal 2026',level_low='20',level_high='20',level_unit='percent',comparison_text='same compared to our fiscal 2025',company_confirmed=True),['Calendar; prior actual comparison is not an earlier-forecast comparison.'])
closing=S('PR003','As a reminder, we anticipate that transaction will close in the second half of calendar 2026.','expected acquisition timing, not a financial amount')
leverage=S('PR004','Our disciplined approach to capital allocation has positioned us well to finance the recently announced agreement with Uniforce. With leverage expected to be about 1.5 times debt to EBITDA at closing, we maintain flexibility for deploying capital across each of our priorities.','company debt/EBITDA level conditional on closing')
A('MAR07','Debt to EBITDA at acquisition closing',[closing,leverage],dict(printed_value='1.5',qualifier='about',measure_text='debt to EBITDA',time_type='instant',period_text='at closing',company_confirmed=True),['Do not invent a closing date or pretend the whole H2 window is an exact instant; resolve permitted period representation.','Acquisition timing forecast itself follows planned-act/outside-approval rules, not automatic separate guidance.'])
cost=B('PR004','As both Todd and Jim have mentioned,','we will break these costs out on our income statement as a separate line item to provide visibility to these transaction related costs.','nonrecurring transaction costs and EPS impact excluded from adjusted guide')
costq=B('QA000','Unknown [783]:','Any costs that were incurred in Q3 were immaterial.','management explicitly assigns the stated EPS impact to both Q4 and fiscal-year guide')
A('MAR08','Annual transaction-cost impact on diluted EPS',[cost,costq],dict(period_text='fiscal 2026',printed_values=['0.03','0.04'],level_unit='usd',measurement_words=['non-recurring transaction costs','impact on diluted earnings per share'],company_confirmed=True),['Preserve cost-impact direction without substituting total EPS; no computed adjusted-to-GAAP forecast.'])
A('MAR09','Q4 transaction-cost impact on diluted EPS',[cost,costq],dict(period_text='fourth quarter',printed_values=['three','four'],level_unit='usd',normalized_amounts=['0.03','0.04'],company_confirmed=True),['Same claim explicitly covers another target period; establish period-specific record and sign.','Amounts and cents wording are stated, not new calculations.'])
scenario=B('QA001','Unknown [901]:','And we have contemplated this in our guide.','conditional fuel sensitivity and general guidance inclusion; numerical assumption not unequivocally adopted')
A('MAR10','Fuel sensitivity versus actual guidance assumption',[scenario,fuel],dict(conditional_input='30% increase in fuel costs',conditional_effect='30 basis points',duration='an entire quarter',company_confirmed_actual_forecast_amount=False),['Adjudicate illustration versus adopted forecast assumption. Preserve broad guide inclusion, but do not automatically make 30% or 30bp a current forecast.'],status='claim_requires_interpretation')
standing=B('QA006','Jim Rosakis [1471]:','You know, we do like to target that mid to high single-digit total growth rate.','standing target; later retention and pricing are current drivers, not new forecasts')
A('MAR11','Standing total growth target',[standing],dict(value_text='mid to high single-digit total growth rate',period_text='every quarter',company_confirmed=True),['Source says total, not organic; resolve recurring horizon without assigning a single fiscal quarter.'])
org=B('QA016','Unknown [2548]:','So really effectively right in line with the guide that we gave last quarter.','company/Q4/organic context, actual and earlier guidance, and two current implied values')
A('MAR12','Q4 implied organic revenue growth',[org],dict(period_text='Q4',level_low='7.6',level_high='7.6',level_unit='unknown',measurement_words=['organic'],company_confirmed=True),['Do not borrow actual Q3 8.2 or prior H2 7.8; fiscal calendar and full measure association required.'])
A('MAR13','H2 implied average organic growth',[org],dict(period_text='second half',level_low='7.9',level_high='7.9',level_unit='unknown',qualifier='average',previous_forecast_values=['7.8'],company_confirmed=True),['Management states 7.9; do not re-compute it or confuse H2 with Q4. Determine stated movement without inventing a revision.'])
A('MAR14','Organic growth guide high end',[org],dict(printed_value='8%',qualifier='at the high end of the range',company_confirmed=True),['Resolve precise current versus previous guided period from discourse; no invented lower endpoint.'],status='claim_requires_association')
A('MAR15','First-aid exceptional prior growth not repeated',[org],dict(business_scope='first aid',period_text='Q4',earlier_actual_value='18.5%',value_text='We certainly do not anticipate that again.',company_confirmed=True),['Earlier 18.5% is not the current point; determine admissible qualitative representation without inventing a precise bound.'])
erp=B('QA022','Unknown [3270]:','because we\'re not anticipating us to be fully rolled out by June 1st.','analyst identifies margin headwind, management confirms full-year scenario and lesser FY27 impact with condition')
A('MAR16','FY27 fire ERP margin impact below full-year scenario',[erp],dict(period_text='next year / 27',printed_reference_value='100 basis points',value_text='something less than that',condition='depending on when we actually go live with the entire business; not fully rolled out by June 1st',business_scope='fire',company_confirmed=True),['The 100bp full-year scenario is not an unconditional actual FY27 point. Preserve both scenario and lesser realized forecast; resolve permitted numeric-bound/worded representation and sign.'])
investment=B('QA009','Unknown [1780]:','So I wouldn\'t say anything, no material change there.','investment continuity, analyst asks FY26 exit/FY27')
A('MAR17','Investment approach/level unchanged',[investment],dict(value_text='no material change',company_confirmed=True),['Determine whether company commits to a level or merely its ongoing approach; do not invent CapEx/revenue or a spending amount.'],status='borderline_claim')
incremental=B('QA020','Unknown [3112]:','That\'s simply what we\'ve been predicting and timing around for the year.','Q4 incrementals described as attractive, no quantity')
A('MAR18','Q4 incremental margins described as attractive',[incremental],dict(period_text='Q4',company_confirmed=True),['Attractive is evaluative language, not necessarily a specific forecast value. No prior target may silently fill it.'],status='borderline_claim')
r.save({
 'PR000':'Operator.', 'PR001':'Disclosure.', 'PR002':'MAR01–04, EPS exclusion and acquisition closing conditions; deal itself not automatic guidance.',
 'PR003':'Reported segment figures; closing-timing context for MAR07.','PR004':'MAR05–09 and shared assumptions; preceding results actual.',
 'PR005':'Broad future strategy.', 'PR006':'Question protocol and no deal-process detail.', 'PR007':'Operator.',
 'QA000':'MAR08/09 period confirmation; past SG&A comparisons not future forecasts.', 'QA001':'MAR10 uncertain sensitivity versus adopted assumption.',
 'QA002':'Current customer behavior.', 'QA003':'Energy assumption; no-fuel-surcharge is current policy, not independent guidance.',
 'QA004':'MAR07 repeated leverage; no specific CapEx ratio guidance confirmed.', 'QA005':'Greeting.',
 'QA006':'MAR11 standing target; actual 95% retention and 2–3% pricing, illustrative arithmetic not independent forecasts.',
 'QA007':'Actual margin drivers and caution on variability; no specific future margin amount.', 'QA008':'Tariff timing/current supply-chain context; nothing material said, no stated forecast level.',
 'QA009':'MAR17 borderline investment outlook.', 'QA010':'Buyback restriction/current policy and future opportunism, no fixed level.', 'QA011':'Greeting.',
 'QA012':'Current wearer/customer levels.', 'QA013':'Acquisition strategy, no promised amount.', 'QA014':'Products/customer example and market opportunity.',
 'QA015':'ERP implementation plans and general benefits, no numeric financial impact.',
 'QA016':'MAR12–15, separate target periods and old/actual/current values.', 'QA017':'Competition/current customer statistics.',
 'QA018':'Routing integration strategy, not quantified forecast.', 'QA019':'Deal opportunities and one-time costs discussed generally; no additional amount or target period.',
 'QA020':'MAR18 evaluative Q4 margin comment.', 'QA021':'Current conversion and employment conditions; broad optimism.',
 'QA022':'MAR16, full question is necessary to identify the headwind and FY27.', 'QA023':'Closing and next results schedule.'})
