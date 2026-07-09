#!/usr/bin/env python3
"""Deterministic 0-LLM drafter for K-pairs.v1 (Fable v1.8 route). NO LLM, NO network, NO grader calls.

Emits into keys/K-pairs/: K-pairs.v1.jsonl (grader-visible) + K-pairs.v1.sidecar.jsonl (adjudication).

Anti-tell design (protocol section 7): lexical overlap and quote length must NOT predict gold. So BOTH classes
span the full overlap range at equal length:
  DIFFERENT = ~56 HIGH-overlap traps (shared root word + shared quote words: homonym/gross-net/adjusted-gaap/
              segment-consolidated/cross-flavor/per-x) + ~54 LOW-overlap traps (disjoint vocabulary:
              bookings-billings/benchmark-siblings/deferred-recognized/genus-species/cause-consequence/ownership).
  SAME      = ~15 HIGH-overlap easy synonyms + ~35 HARD (same driver, DIFFERENT vocabulary -> LOW overlap).
Quotes are realistic filing language grounded in the 12-company corpus; planted synthetic-but-realistic is legal
(protocol section 5). Quotes are length-matched (~52-64 chars). key_lint.py enforces the balance."""
import json
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "keys", "K-pairs")
R, A, T, P, M = "restaurants", "airlines", "retail", "auto_parts", "macro"
DATA = []


def mk(fam, gold, ind_a, na, qa, nb, qb, hard=False, ind_b=None, pxa=None, pxb=None,
       sla=None, slb=None, grounding="synthetic", src="synthetic-realistic", rat="", tell=""):
    DATA.append(dict(fam=fam, gold=gold, hard=hard, ind_a=ind_a, ind_b=ind_b or ind_a, na=na, qa=qa, nb=nb, qb=qb,
                     pxa=pxa, pxb=pxb, sla=sla or [], slb=slb or [], grounding=grounding, src=src, rat=rat, tell=tell))


# ================= DIFFERENT: LOW-overlap families (disjoint vocabulary) =================

# bookings_billings (9) LOW
mk("bookings_billings", "DIFFERENT", A, "advance ticket sales", "Travelers prepaid trips scheduled for later departure.",
   "passenger revenue", "Fares convert to earned income once a flight operates.", hard=True,
   src="AAL/LUV air traffic liability vs passenger revenue", rat="Cash booked ahead is a liability; passenger revenue is the recognized amount.", tell="order side vs recognized side, disjoint words")
mk("bookings_billings", "DIFFERENT", R, "catering orders booked", "Guests reserved large event menus for upcoming dates.",
   "catering revenue", "Amounts post to the ledger after each event is delivered.",
   src="DRI/CAKE", rat="Booked demand vs recognized catering revenue.")
mk("bookings_billings", "DIFFERENT", T, "online orders placed", "Shoppers submitted digital carts during the promotion.",
   "net sales on shipment", "Recognition happens when merchandise leaves the warehouse.",
   src="BBY", rat="Orders placed (demand) vs recognized net sales on shipment.")
mk("bookings_billings", "DIFFERENT", P, "commercial orders booked", "Repair shops committed to parts for scheduled jobs ahead.",
   "commercial sales invoiced", "Billing posts upon delivery to the professional account.",
   src="AZO/ORLY commercial", rat="Orders booked vs invoiced commercial sales.")
mk("bookings_billings", "DIFFERENT", R, "reservations booked", "Diners held tables through our platform before arriving.",
   "dine-in sales recorded", "The register captures amounts at the moment guests pay.",
   src="DRI", rat="Bookings of demand vs recorded sales.")
mk("bookings_billings", "DIFFERENT", T, "customer order backlog", "Unfilled appliance commitments stayed elevated at close.",
   "revenue on delivery", "Recognition follows install and handoff to the household.",
   src="BBY", rat="Backlog of committed orders vs recognized revenue.")
mk("bookings_billings", "DIFFERENT", P, "orders reserved for pickup", "Buyers held items to collect later at the counter.",
   "in-store sales rung up", "Checkout scanning marks the point of recognition.",
   src="AZO", rat="Reserved demand vs sales rung up.")
mk("bookings_billings", "DIFFERENT", A, "advance bookings", "Forward demand for next quarter ran ahead of last year.",
   "current period passenger revenue", "Completed flights drive the amount earned this quarter.",
   src="LUV", rat="Forward demand vs current recognized revenue.")
mk("bookings_billings", "DIFFERENT", R, "loyalty points issued", "Members accumulated rewards from their recent visits.",
   "loyalty breakage income", "Expired unredeemed balances flow to the income line.",
   src="MCD/CMG", rat="Points issued (obligation) vs breakage recognized.")

# benchmark_siblings (9) LOW
mk("benchmark_siblings", "DIFFERENT", M, "Brent crude price", "The international seaborne oil marker set global pricing.",
   "WTI crude price", "West Texas grade tracks landlocked American barrels.", hard=True,
   src="fuel drivers", rat="Two distinct oil benchmarks, not interchangeable.", tell="sibling benchmarks, low overlap but DIFFERENT")
mk("benchmark_siblings", "DIFFERENT", M, "SOFR", "The secured overnight rate anchors floating bank debt.",
   "federal funds rate", "A policy target the central bank sets for reserves.", hard=True,
   src="interest drivers", rat="Related but distinct reference rates.")
mk("benchmark_siblings", "DIFFERENT", A, "jet fuel price", "Refined kerosene trades at a spread above the barrel.",
   "crude oil price", "Unrefined feedstock quoted before any processing step.", hard=True,
   src="AAL/LUV fuel", rat="Jet fuel vs crude: correlated but distinct inputs.")
mk("benchmark_siblings", "DIFFERENT", R, "beef commodity cost", "Cattle market swings drive this primary protein input.",
   "chicken commodity cost", "Poultry supply cycles move a separate menu ingredient.", hard=True,
   src="restaurant basket", rat="Distinct protein commodities.")
mk("benchmark_siblings", "DIFFERENT", M, "10-year Treasury yield", "Long-dated government paper reflects distant expectations.",
   "2-year Treasury yield", "Short maturities track near-term policy bets instead.", hard=True,
   src="rate curve", rat="Different maturities on the curve.")
mk("benchmark_siblings", "DIFFERENT", M, "CPI inflation", "A fixed household basket gauges consumer price change.",
   "PCE inflation", "Shifting spending weights measure deflator movement.", hard=True,
   src="inflation drivers", rat="Two distinct inflation gauges.")
mk("benchmark_siblings", "DIFFERENT", M, "diesel fuel price", "Over-the-road freight tracks the pump cost of trucks.",
   "natural gas price", "Facility heating and utilities follow the gas market.", hard=True,
   src="AZO/ORLY distribution", rat="Two distinct energy inputs.")
mk("benchmark_siblings", "DIFFERENT", M, "euro-dollar rate", "European sourcing shifts with the single-currency cross.",
   "broad dollar index", "Overall import buying power follows a trade-weighted basket.", hard=True,
   src="ULTA/BBY sourcing", rat="A pair rate vs a basket index.")
mk("benchmark_siblings", "DIFFERENT", R, "cheese commodity cost", "Block dairy markets set the price of this topping input.",
   "avocado cost", "Agricultural produce cycles govern a separate ingredient.", hard=True,
   src="CMG/YUM basket", rat="Distinct commodity inputs.")

# deferred_recognized (9) LOW
mk("deferred_recognized", "DIFFERENT", T, "gift card liability", "Unredeemed prepaid cards sit as an obligation on the books.",
   "gift card revenue", "Redemption and breakage turn cards into earned income.", hard=True,
   src="BBY/ULTA", rat="Liability balance vs recognized revenue.", tell="liability vs recognized, disjoint words")
mk("deferred_recognized", "DIFFERENT", R, "deferred loyalty revenue", "Points owed to members await future redemption events.",
   "loyalty revenue recognized", "Earned income posts as rewards are cashed or expire.", hard=True,
   src="MCD/CMG rewards", rat="Deferred obligation vs recognized loyalty revenue.")
mk("deferred_recognized", "DIFFERENT", A, "air traffic liability", "Tickets held for future travel carry an unearned balance.",
   "passenger revenue earned", "Completing the trip converts the balance into income.",
   src="LUV", rat="Unearned ticket liability vs earned revenue.")
mk("deferred_recognized", "DIFFERENT", T, "deferred membership fees", "Prepaid program dues amortize across the coverage term.",
   "membership fee income", "Ratable recognition posts each month of the plan.",
   src="BBY Totaltech", rat="Deferred fee balance vs recognized income.")
mk("deferred_recognized", "DIFFERENT", R, "contract liability", "Consideration collected before performance sits deferred.",
   "recognized revenue", "Satisfying an obligation moves the amount into income.",
   src="DRI", rat="Contract liability vs recognized revenue.")
mk("deferred_recognized", "DIFFERENT", A, "loyalty deferred balance", "Outstanding miles represent a duty owed to members.",
   "loyalty revenue", "Redeeming those miles for travel books the income.",
   src="AAL AAdvantage", rat="Deferred miles vs recognized loyalty revenue.")
mk("deferred_recognized", "DIFFERENT", T, "unearned service revenue", "Prepaid installs not yet performed remain a liability.",
   "service revenue recognized", "Completing the work moves amounts to earned income.",
   src="BBY services", rat="Unearned vs recognized service revenue.")
mk("deferred_recognized", "DIFFERENT", R, "deferred franchise fees", "Upfront amounts spread across the multi-year agreement.",
   "franchise royalty revenue", "Ongoing income accrues as operator sales occur.", hard=True,
   src="YUM", rat="Deferred initial fee vs ongoing royalty.")
mk("deferred_recognized", "DIFFERENT", P, "customer deposits", "Prepayments on special orders await the arrival of parts.",
   "recognized sales", "Delivery of the ordered item books the transaction.",
   src="ORLY", rat="Advance deposits vs recognized sales.")

# genus_species (9) LOW
mk("genus_species", "DIFFERENT", R, "total revenue", "Every source across the company rolls into the top line.",
   "beverage revenue", "Only drinks contribute to this narrow product slice.", hard=True, sla=["product"],
   src="product mix", rat="Total (genus) vs a beverage species.", tell="a part vs the whole")
mk("genus_species", "DIFFERENT", A, "total operating expenses", "Salaries, upkeep, rent and more sum into the full cost.",
   "aircraft maintenance expense", "Only fleet repair work lands in this narrower line.",
   src="AAL", rat="All opex (genus) vs maintenance (species).")
mk("genus_species", "DIFFERENT", T, "merchandise revenue", "All product categories combine into one broad figure.",
   "computing revenue", "Just laptops and tablets feed this single category.", sla=["product"],
   src="BBY category", rat="All merchandise (genus) vs one category (species).")
mk("genus_species", "DIFFERENT", P, "cost of sales", "Merchandise and freight together form the full amount.",
   "freight cost", "Inbound transport alone makes up this narrow piece.",
   src="AZO", rat="Total cost of sales (genus) vs freight (species).")
mk("genus_species", "DIFFERENT", R, "labor and related expense", "Wages, benefits and taxes combine into staffing cost.",
   "payroll tax expense", "Only the employer levy sits in this smaller line.",
   src="DRI", rat="Total labor (genus) vs payroll tax (species).")
mk("genus_species", "DIFFERENT", A, "passenger revenue", "Fares plus onboard charges make up the broad figure.",
   "seat selection revenue", "Just the choose-your-seat fee feeds this narrow slice.",
   src="LUV ancillary", rat="Passenger revenue (genus) vs a fee (species).")
mk("genus_species", "DIFFERENT", T, "comparable sales", "Growth across every like-for-like channel is combined.",
   "in-store comparable sales", "Only physical locations feed this narrower measure.", sla=["channel"],
   src="ULTA", rat="All comps (genus) vs in-store comps (species).")
mk("genus_species", "DIFFERENT", R, "food and beverage costs", "All ingredients and drinks together form the figure.",
   "produce cost", "Just fresh vegetables and fruit sit in this line.",
   src="CMG", rat="Total food cost (genus) vs produce (species).")
mk("genus_species", "DIFFERENT", A, "operating revenue", "Passengers, freight and other sources sum together.",
   "cargo revenue", "Only hold freight contributes to this narrow amount.",
   src="DAL", rat="Operating revenue (genus) vs cargo (species).")

# cause_consequence (9) LOW
mk("cause_consequence", "DIFFERENT", A, "fuel price spike", "A sharp jump in the market rate pressured the quarter.",
   "fuel expense", "The income statement line reflects reported cost burned.", hard=True,
   src="AAL", rat="Market move (cause) vs the reported line (consequence).", tell="cause vs consequence")
mk("cause_consequence", "DIFFERENT", R, "wage inflation", "Tight hiring markets pushed hourly pay steadily higher.",
   "labor expense", "The staffing line on the statement moved up as a result.", hard=True,
   src="restaurant labor", rat="Wage inflation (cause) vs labor expense (consequence).")
mk("cause_consequence", "DIFFERENT", R, "severe winter storms", "Bad weather kept many guests away from dining rooms.",
   "comparable sales decline", "The reported like-for-like figure fell versus last year.", hard=True,
   src="DRI/CAKE weather", rat="Weather (cause) vs comps decline (consequence).")
mk("cause_consequence", "DIFFERENT", M, "policy rate hikes", "The central bank lifted its target several times.",
   "interest expense", "The reported cost of borrowings climbed accordingly.", hard=True,
   src="rate-driven", rat="Rate hikes (cause) vs interest expense (consequence).")
mk("cause_consequence", "DIFFERENT", R, "commodity cost inflation", "Pricier beef and dairy lifted the cost of ingredients.",
   "margin compression", "Restaurant-level profitability narrowed as a result.", hard=True,
   src="CMG", rat="Input inflation (cause) vs margin compression (consequence).")
mk("cause_consequence", "DIFFERENT", T, "heavy promotional activity", "Deep discounts were used to move slow-selling inventory.",
   "gross margin decline", "The reported profitability rate slipped year over year.", hard=True,
   src="BBY", rat="Discounting (cause) vs margin decline (consequence).")
mk("cause_consequence", "DIFFERENT", A, "capacity oversupply", "Too many seats chased limited demand on key routes.",
   "unit revenue decline", "Reported revenue per seat mile weakened accordingly.", pxb="available seat mile", hard=True,
   src="DAL RASM", rat="Oversupply (cause) vs RASM decline (consequence).")
mk("cause_consequence", "DIFFERENT", P, "rapid store openings", "An accelerated build-out widened the physical footprint.",
   "pre-opening expense", "Costs before doors open showed up as a reported charge.",
   src="ORLY", rat="Openings (cause) vs pre-opening expense (consequence).")
mk("cause_consequence", "DIFFERENT", T, "port and freight snarls", "Shipping bottlenecks delayed inbound merchandise flow.",
   "out-of-stock levels", "Empty shelves rose across several important categories.",
   src="BBY", rat="Disruption (cause) vs out-of-stocks (consequence).")

# ownership_axis (9) LOW
mk("ownership_axis", "DIFFERENT", R, "company-operated restaurant sales", "Locations we run directly generate these amounts.",
   "franchised restaurant sales", "Independently owned operators produce this figure.", hard=True,
   src="MCD/YUM", rat="Same metric, different ownership class.", tell="company vs franchise ownership")
mk("ownership_axis", "DIFFERENT", R, "company-operated margin", "Profitability at units we own and run directly.",
   "franchise margin", "Royalty income net of operator support programs.", hard=True,
   src="MCD", rat="Company-operated vs franchise economics.")
mk("ownership_axis", "DIFFERENT", A, "mainline unit cost", "Aircraft we fly ourselves carry this per-seat figure.",
   "regional unit cost", "Capacity purchased from affiliates carries another.", pxa="available seat mile", pxb="available seat mile",
   src="AAL/DAL", rat="Directly-operated vs purchased regional capacity.")
mk("ownership_axis", "DIFFERENT", P, "company-owned store count", "Outlets we operate ourselves make up this tally.",
   "independent dealer count", "Third-party owned resellers form a separate roster.",
   src="auto parts", rat="Owned vs independent outlets.")
mk("ownership_axis", "DIFFERENT", R, "owned real estate", "Properties held in fee title sit on our balance sheet.",
   "leased real estate", "Sites rented under operating agreements are separate.",
   src="MCD", rat="Owned vs leased property.")
mk("ownership_axis", "DIFFERENT", R, "system restaurant count", "Every unit, company and operator alike, is included.",
   "company restaurant count", "Only locations we run ourselves make this tally.", hard=True,
   src="YUM", rat="System (all ownership) vs company-only.")
mk("ownership_axis", "DIFFERENT", A, "consolidated venture result", "A controlled entity is folded fully into our figures.",
   "equity-method venture result", "A minority stake appears as one net investment line.", hard=True,
   src="airline JV", rat="Consolidated vs equity-method treatment.")
mk("ownership_axis", "DIFFERENT", R, "franchise royalty revenue", "A slice of operator sales flows to us as fees.",
   "company sales revenue", "Locations we run book their own transactions instead.",
   src="YUM/MCD", rat="Royalty (franchise) vs company sales.")
mk("ownership_axis", "DIFFERENT", P, "company distribution centers", "Warehouses we own and staff handle our flow.",
   "third-party logistics", "Outsourced providers fulfill on a contract basis.",
   src="AZO", rat="Owned DCs vs outsourced logistics.")

# ================= DIFFERENT: HIGH-overlap families (shared root + shared quote words) =================

# channel_homonym (10) HIGH (same/near name, shared framing)
mk("channel_homonym", "DIFFERENT", R, "traffic", "Traffic counts the guests visiting our restaurants.",
   "traffic", "Traffic counts the shoppers visiting our stores.", hard=True, ind_b=T,
   src="homonym traffic", rat="Restaurant guest count vs retail foot-traffic.", tell="identical name, cross-industry -> DIFFERENT")
mk("channel_homonym", "DIFFERENT", A, "capacity", "Capacity measures available seat miles across the fleet.",
   "capacity", "Capacity measures throughput across the distribution fleet.", hard=True, ind_b=T, pxa="available seat mile",
   src="homonym capacity", rat="Airline seat capacity vs DC throughput capacity.")
mk("channel_homonym", "DIFFERENT", A, "yield", "Yield measures revenue earned per passenger mile flown.",
   "yield", "Yield measures the dividend earned per share held.", hard=True, ind_b=M, pxa="revenue passenger mile",
   src="homonym yield", rat="Airline yield vs dividend yield.")
mk("channel_homonym", "DIFFERENT", R, "unit", "A unit means one restaurant location in the count.",
   "unit", "A unit means one seat mile in the revenue rate.", hard=True, ind_b=A, pxb="available seat mile",
   src="homonym unit", rat="Store unit vs airline per-ASM unit.")
mk("channel_homonym", "DIFFERENT", P, "comps", "Comps means comparable-store sales at open stores.",
   "comps", "Comps means complimentary meals given to guests.", hard=True, ind_b=R,
   src="homonym comps", rat="Comparable sales vs complimentary meals.")
mk("channel_homonym", "DIFFERENT", A, "load factor", "Load factor gives the share of seats sold on flights.",
   "utilization", "Utilization gives the share of hours each aircraft flies.", ind_b=A,
   src="near homonym", rat="Seat fill vs asset utilization.")
mk("channel_homonym", "DIFFERENT", R, "cover", "A cover means one guest served during a meal period.",
   "coverage", "Coverage means earnings measured against interest owed.", hard=True, ind_b=M,
   src="homonym cover(age)", rat="Restaurant covers vs interest coverage.")
mk("channel_homonym", "DIFFERENT", T, "basket", "The basket means average spend per shopping trip.",
   "basket", "The basket means the weighted mix of input costs.", hard=True, ind_b=R,
   src="homonym basket", rat="Retail basket vs commodity basket.")
mk("channel_homonym", "DIFFERENT", A, "stage length", "Stage length gives the average miles flown per trip.",
   "length of stay", "Length of stay gives the average nights booked per guest.", ind_b=R,
   src="near homonym", rat="Airline stage length vs hospitality stay.")
mk("channel_homonym", "DIFFERENT", R, "check", "A check means the amount a guest pays for a meal.",
   "check", "A check means a printed instrument used to pay a balance.", hard=True, ind_b=M,
   src="homonym check", rat="Restaurant check vs payment check.")

# gross_net (9) HIGH (shared root: margin/sales/revenue + shared framing)
mk("gross_net", "DIFFERENT", R, "system-wide sales", "System-wide sales include franchised and company sales.",
   "company sales", "Company sales include only the company-operated sales.", hard=True,
   src="YUM/MCD", rat="Gross system sales vs the company's own sales.", tell="gross system vs net company")
mk("gross_net", "DIFFERENT", A, "gross passenger revenue", "Gross passenger revenue is stated before taxes collected.",
   "net passenger revenue", "Net passenger revenue is stated after taxes remitted.",
   src="DAL", rat="Gross vs net of pass-through taxes.")
mk("gross_net", "DIFFERENT", T, "gross merchandise value", "Gross merchandise value counts all marketplace orders.",
   "net revenue", "Net revenue counts only the commission we retain.", hard=True,
   src="BBY marketplace", rat="GMV (gross) vs net revenue as agent.")
mk("gross_net", "DIFFERENT", P, "gross sales", "Gross sales are total sales before returns are removed.",
   "net sales", "Net sales are total sales after returns are removed.",
   src="ORLY", rat="Gross vs net of returns.")
mk("gross_net", "DIFFERENT", R, "gross margin", "Gross margin is revenue left after ingredient cost.",
   "operating margin", "Operating margin is revenue left after every cost.",
   src="CMG", rat="Gross margin vs operating margin.")
mk("gross_net", "DIFFERENT", A, "gross bookings", "Gross bookings are fare amounts before refunds are removed.",
   "net revenue", "Net revenue is fare amounts after refunds are removed.",
   src="AAL", rat="Gross bookings vs net recognized revenue.")
mk("gross_net", "DIFFERENT", T, "gross margin dollars", "Gross margin dollars are revenue minus merchandise cost.",
   "net margin", "Net margin is income shown as a percentage of revenue.",
   src="ULTA", rat="Gross margin dollars vs net margin ratio.")
mk("gross_net", "DIFFERENT", R, "gross franchise revenue", "Gross franchise revenue includes ad-fund amounts collected.",
   "net franchise revenue", "Net franchise revenue excludes ad-fund amounts collected.",
   src="YUM", rat="Gross vs net of advertising-fund pass-through.")
mk("gross_net", "DIFFERENT", P, "gross profit margin", "Gross profit margin is revenue after merchandise cost.",
   "operating margin", "Operating margin is revenue after all store costs.",
   src="AZO", rat="Gross-level vs operating-level margin.")

# adjusted_vs_gaap (9) HIGH (shared root metric; adjusted excludes items)
mk("adjusted_vs_gaap", "DIFFERENT", R, "adjusted operating income", "Adjusted operating income excludes restructuring charges.",
   "operating income", "Operating income includes those restructuring charges.", hard=True,
   src="restaurant 8-K", rat="Same line; one excludes items, one does not.", tell="adjusted non-GAAP vs GAAP")
mk("adjusted_vs_gaap", "DIFFERENT", T, "adjusted operating income", "Adjusted operating income excludes store-closing costs.",
   "operating income", "Operating income includes those store-closing costs.", hard=True,
   src="BBY 8-K", rat="Same line, item exclusion differs.")
mk("adjusted_vs_gaap", "DIFFERENT", R, "adjusted diluted EPS", "Adjusted diluted EPS excludes a legal settlement charge.",
   "diluted EPS", "Diluted EPS includes the legal settlement charge in full.", hard=True,
   src="YUM/MCD", rat="Adjusted EPS removes an item; GAAP EPS does not.")
mk("adjusted_vs_gaap", "DIFFERENT", A, "adjusted pre-tax income", "Adjusted pre-tax income excludes special mark-to-market items.",
   "pre-tax income", "Pre-tax income includes those special mark-to-market items.",
   src="AAL/DAL", rat="Special-item exclusion distinguishes them.")
mk("adjusted_vs_gaap", "DIFFERENT", T, "adjusted gross margin", "Adjusted gross margin excludes purchase-accounting amounts.",
   "gross margin", "Gross margin includes those purchase-accounting amounts.",
   src="ULTA", rat="Adjustment removes purchase-accounting effects.")
mk("adjusted_vs_gaap", "DIFFERENT", R, "adjusted operating margin", "Adjusted operating margin excludes non-representative items.",
   "operating margin", "Operating margin includes every item under the rules.",
   src="CMG", rat="'Core' non-GAAP variant vs the GAAP margin.")
mk("adjusted_vs_gaap", "DIFFERENT", A, "adjusted unit cost", "Adjusted unit cost excludes fuel and special charges.",
   "reported unit cost", "Reported unit cost includes fuel and special charges.", pxa="available seat mile", pxb="available seat mile",
   src="AAL/LUV", rat="Ex-fuel adjusted cost vs all-in reported cost.")
mk("adjusted_vs_gaap", "DIFFERENT", P, "adjusted net income", "Adjusted net income excludes a one-time pension charge.",
   "net income", "Net income includes the one-time pension charge in full.",
   src="AZO", rat="Adjusted excludes an item; GAAP includes it.")
mk("adjusted_vs_gaap", "DIFFERENT", T, "adjusted SG&A", "Adjusted SG&A excludes transformation and severance costs.",
   "SG&A expense", "SG&A expense includes transformation and severance costs.",
   src="BBY", rat="Non-GAAP expense vs the GAAP expense line.")

# segment_consolidated (9) HIGH (shared metric word; part vs whole)
mk("segment_consolidated", "DIFFERENT", R, "division operating profit", "Division operating profit reflects one brand's restaurants.",
   "consolidated operating profit", "Consolidated operating profit reflects all brands combined.", hard=True,
   src="YUM segments", rat="One brand's segment result vs the total.", tell="segment vs consolidated")
mk("segment_consolidated", "DIFFERENT", A, "mainline operating revenue", "Mainline operating revenue reflects our own jets only.",
   "consolidated operating revenue", "Consolidated operating revenue reflects mainline plus regional.", hard=True,
   src="AAL/DAL", rat="Mainline segment vs consolidated total.")
mk("segment_consolidated", "DIFFERENT", T, "services segment revenue", "Services segment revenue reflects memberships and repair.",
   "total revenue", "Total revenue reflects products and services combined.",
   src="BBY services", rat="One segment vs total revenue.")
mk("segment_consolidated", "DIFFERENT", R, "brand segment sales", "Brand segment sales reflect one division's performance.",
   "total company sales", "Total company sales reflect all divisions together.",
   src="YUM", rat="Brand segment vs total company.")
mk("segment_consolidated", "DIFFERENT", P, "domestic segment revenue", "Domestic segment revenue reflects United States stores.",
   "consolidated revenue", "Consolidated revenue reflects domestic and overseas stores.", sla=["geography"],
   src="AZO", rat="Geographic segment vs consolidated.")
mk("segment_consolidated", "DIFFERENT", A, "cargo segment revenue", "Cargo segment revenue reflects freight operations only.",
   "total operating revenue", "Total operating revenue reflects passenger and freight.",
   src="AAL cargo", rat="Cargo segment vs total.")
mk("segment_consolidated", "DIFFERENT", R, "company-restaurant segment margin", "Company-restaurant segment margin reflects operated units.",
   "consolidated operating margin", "Consolidated operating margin reflects franchise and corporate.",
   src="MCD", rat="Segment margin vs consolidated margin.")
mk("segment_consolidated", "DIFFERENT", T, "salon services revenue", "Salon services revenue reflects in-store salon activity.",
   "total net sales", "Total net sales reflect merchandise and services company-wide.",
   src="ULTA salon", rat="Service sub-segment vs total.")
mk("segment_consolidated", "DIFFERENT", A, "regional segment cost", "Regional segment cost reflects purchased affiliate flying.",
   "consolidated operating cost", "Consolidated operating cost reflects mainline and regional.",
   src="DAL regional", rat="Regional segment cost vs consolidated cost.")

# cross_flavor (10) HIGH (same word, different level/basis)
mk("cross_flavor", "DIFFERENT", T, "gross margin", "Gross margin is revenue left after cost of goods.",
   "operating margin", "Operating margin is revenue left after operating costs.", hard=True,
   src="BBY", rat="Two different margin levels.", tell="same word 'margin', different level")
mk("cross_flavor", "DIFFERENT", R, "operating margin", "Operating margin is profit over revenue after corporate.",
   "restaurant-level margin", "Restaurant-level margin is profit over revenue before corporate.", hard=True,
   src="CMG", rat="Consolidated margin vs four-wall margin.")
mk("cross_flavor", "DIFFERENT", A, "operating income", "Operating income measures accrual profit from operations.",
   "operating cash flow", "Operating cash flow measures actual cash from operations.", hard=True,
   src="AAL", rat="Accrual income vs cash flow.")
mk("cross_flavor", "DIFFERENT", R, "same-store sales growth", "Same-store sales growth compares against the prior year.",
   "sequential sales growth", "Sequential sales growth compares against the prior quarter.", hard=True,
   src="comps", rat="Year-over-year vs sequential basis.")
mk("cross_flavor", "DIFFERENT", P, "nominal sales growth", "Nominal sales growth includes the effect of price rises.",
   "real sales growth", "Real sales growth removes the effect of price rises.", hard=True,
   src="AZO", rat="Nominal vs inflation-adjusted.")
mk("cross_flavor", "DIFFERENT", A, "reported revenue", "Reported revenue is measured at actual exchange rates.",
   "constant-currency revenue", "Constant-currency revenue is measured at fixed rates.", hard=True,
   src="airline FX", rat="Reported vs constant-currency basis.")
mk("cross_flavor", "DIFFERENT", T, "unit sales", "Unit sales measure the count of items sold to buyers.",
   "dollar sales", "Dollar sales measure the value of items sold to buyers.", hard=True,
   src="BBY", rat="Volume vs value.")
mk("cross_flavor", "DIFFERENT", R, "EBITDA margin", "EBITDA margin is earnings over revenue before charges.",
   "net margin", "Net margin is earnings over revenue after all charges.", hard=True,
   src="restaurant", rat="Different profit measures, same word 'margin'.")
mk("cross_flavor", "DIFFERENT", A, "block hours", "Block hours measure time from gate push to gate arrival.",
   "flight hours", "Flight hours measure time from wheels up to wheels down.",
   src="airline ops", rat="Two different time measures.")
mk("cross_flavor", "DIFFERENT", T, "bookings growth", "Bookings growth measures orders placed against last year.",
   "revenue growth", "Revenue growth measures recognized sales against last year.", hard=True,
   src="BBY", rat="Growth of orders vs recognized revenue.")

# per_x (9) HIGH (shared base word: revenue/cost/sales; per-unit vs aggregate)
mk("per_x", "DIFFERENT", A, "revenue per available seat mile", "Passenger revenue divided by seat miles gives this rate.",
   "total passenger revenue", "Passenger revenue summed across the network gives the total.", hard=True, pxa="available seat mile",
   src="DAL RASM", rat="Normalized unit rate vs the aggregate.", tell="per-X vs aggregate, share 'passenger revenue'")
mk("per_x", "DIFFERENT", T, "sales per square foot", "Net sales divided by selling area gives this productivity.",
   "total net sales", "Net sales summed across all stores gives the aggregate.", hard=True, pxa="square foot",
   src="ULTA/BBY", rat="Per-square-foot productivity vs total sales.")
mk("per_x", "DIFFERENT", A, "cost per available seat mile", "Operating cost divided by seat miles gives this rate.",
   "total operating cost", "Operating cost summed for the period gives the total.", pxa="available seat mile",
   src="LUV CASM", rat="Unit cost vs total cost.")
mk("per_x", "DIFFERENT", R, "average unit volume", "Restaurant sales divided by units gives this per-store rate.",
   "total restaurant sales", "Restaurant sales summed across units gives the total.", pxa="restaurant",
   src="CMG AUV", rat="Per-restaurant volume vs total sales.")
mk("per_x", "DIFFERENT", R, "average check", "Restaurant sales divided by guests gives this per-guest amount.",
   "total restaurant sales", "Restaurant sales summed across guests gives the total.", pxa="guest",
   src="DRI check", rat="Per-guest check vs total sales.")
mk("per_x", "DIFFERENT", P, "sales per store", "Total sales divided by store count gives this per-store rate.",
   "total sales", "Total sales summed across the chain gives the aggregate.", pxa="store",
   src="ORLY", rat="Per-store sales vs total.")
mk("per_x", "DIFFERENT", A, "revenue per passenger", "Passenger revenue divided by travelers gives this per-head rate.",
   "total passenger revenue", "Passenger revenue summed for the period gives the total.", pxa="passenger",
   src="AAL", rat="Per-passenger revenue vs aggregate.")
mk("per_x", "DIFFERENT", T, "revenue per member", "Total revenue divided by members gives this per-member rate.",
   "total revenue", "Total revenue summed across the company gives the aggregate.", pxa="member",
   src="ULTA loyalty", rat="Per-member revenue vs total.")
mk("per_x", "DIFFERENT", A, "fuel cost per gallon", "Fuel spend divided by gallons gives this per-gallon price.",
   "total fuel expense", "Fuel spend summed for the period gives the total expense.", pxa="gallon",
   src="LUV fuel", rat="Per-gallon price vs total fuel expense.")


# ================= SAME (50) : ~15 easy (HIGH overlap) + ~35 hard (LOW overlap) =================

# --- easy synonyms (HIGH overlap: shared name + shared quote words) ---
mk("synonym", "SAME", T, "net sales", "Net sales are company revenue after returns and allowances.",
   "total net sales", "Total net sales are company revenue after returns too.",
   src="BBY", rat="Same measure, near-identical wording.")
mk("synonym", "SAME", R, "total revenue", "Total revenue includes company sales and franchise royalties.",
   "total revenues", "Total revenues include company sales and franchise royalties.",
   src="YUM", rat="Singular vs plural of the same line.")
mk("synonym", "SAME", P, "comparable store sales", "Comparable store sales cover stores open at least one year.",
   "comparable sales", "Comparable sales cover stores open at least one year too.",
   src="AZO/ORLY", rat="Same comps metric, shorter name.")
mk("synonym", "SAME", R, "same-store sales", "Same-store sales compare locations open in both periods.",
   "same-store sales growth", "Same-store sales growth compares locations open in both periods.",
   src="DRI", rat="Same metric.")
mk("synonym", "SAME", A, "available seat miles", "Available seat miles are seats flown times the miles flown.",
   "ASMs", "ASMs are seats flown times the miles flown, abbreviated.",
   src="LUV", rat="Full vs abbreviation.")
mk("synonym", "SAME", A, "cost per available seat mile", "Cost per available seat mile is operating cost per seat mile.",
   "CASM", "CASM is operating cost per available seat mile, abbreviated.", pxa="available seat mile", pxb="available seat mile",
   src="AAL", rat="Full vs abbreviation.")
mk("synonym", "SAME", R, "gross profit margin", "Gross profit margin is gross profit over revenue as a percent.",
   "gross margin", "Gross margin is gross profit over revenue as a percent too.",
   src="CMG", rat="Same margin, slight wording.")
mk("synonym", "SAME", A, "passenger load factor", "Passenger load factor is revenue passenger miles over seat miles.",
   "load factor", "Load factor is revenue passenger miles over seat miles too.",
   src="LUV", rat="Same metric, short form.")
mk("synonym", "SAME", R, "average unit volume", "Average unit volume is average annual sales per restaurant.",
   "AUV", "AUV is average annual sales per restaurant, abbreviated.", pxa="restaurant", pxb="restaurant",
   src="CMG", rat="Full vs abbreviation.")
mk("synonym", "SAME", R, "system-wide sales", "System-wide sales include company and franchised locations.",
   "systemwide sales", "Systemwide sales include company and franchised locations.",
   src="YUM", rat="Spelling variant of the same metric.")
mk("synonym", "SAME", A, "aircraft fuel expense", "Aircraft fuel expense is the cost of jet fuel consumed.",
   "fuel expense", "Fuel expense is the cost of jet fuel consumed by aircraft.",
   src="AAL", rat="Same expense line.")
mk("synonym", "SAME", T, "selling, general and administrative expenses", "These expenses cover store payroll, advertising and overhead.",
   "SG&A expense", "SG&A expense covers store payroll, advertising and overhead.",
   src="ULTA", rat="Full name vs abbreviation.")
mk("synonym", "SAME", P, "cost of goods sold", "Cost of goods sold covers merchandise and inbound freight.",
   "cost of sales", "Cost of sales covers merchandise and inbound freight too.",
   src="AZO", rat="Same cost line here.")
mk("synonym", "SAME", R, "diluted earnings per share", "Diluted earnings per share reflect all dilutive securities.",
   "diluted EPS", "Diluted EPS reflect all dilutive securities, abbreviated.",
   src="MCD", rat="Full vs abbreviation.")
mk("synonym", "SAME", R, "same-restaurant sales", "Same-restaurant sales compare restaurants open in both periods.",
   "comparable restaurant sales", "Comparable restaurant sales compare restaurants open both periods.",
   src="DRI/CAKE", rat="Same comparable-sales metric.")

# --- HARD SAME (same driver, DIFFERENT vocabulary -> LOW overlap) ---
mk("synonym", "SAME", R, "average check", "The typical amount a diner pays per visit rose modestly.",
   "average ticket", "Mean spend on each guest transaction moved up a little.", hard=True,
   src="DRI/CAKE", rat="Same per-guest spend; different jargon.", tell="hard SAME, disjoint words")
mk("synonym", "SAME", R, "average check", "How much a diner pays on a typical visit ticked higher.",
   "average spend per guest", "Total receipts divided across patrons served edged upward.", hard=True,
   src="MCD", rat="Same metric, fully different phrasing.")
mk("synonym", "SAME", R, "guest counts", "The number of diners served during the period improved.",
   "traffic", "How many people walked into our locations picked up.", hard=True,
   src="MCD/YUM", rat="Within restaurants, both mean the same driver.", tell="hard SAME mirroring the traffic homonym")
mk("synonym", "SAME", R, "crew labor cost", "Wages paid to hourly kitchen and counter staff climbed.",
   "payroll and benefits", "Compensation for restaurant employees, all in, rose.", hard=True,
   src="CMG", rat="Same labor driver, different words.")
mk("synonym", "SAME", R, "food and paper costs", "Ingredient and packaging spend moved with commodity prices.",
   "cost of sales", "What we consume to serve each order tracked input markets.", hard=True,
   src="MCD", rat="Same restaurant input cost.")
mk("synonym", "SAME", R, "commodity costs", "Wholesale prices of core ingredients pressured the quarter.",
   "food costs", "What we pay for menu inputs weighed on results.", hard=True,
   src="CMG/YUM", rat="Same input-cost driver.")
mk("synonym", "SAME", R, "occupancy costs", "Expenses tied to holding restaurant premises rose.",
   "rent and related expenses", "Lease and property charges for our locations increased.", hard=True,
   src="DRI", rat="Same premises cost, different words.")
mk("synonym", "SAME", T, "shrink", "Stock lost to theft, damage and error weighed on margin.",
   "inventory shortage", "Merchandise that vanished from the count hurt profitability.", hard=True,
   src="BBY/ULTA", rat="Same loss driver; jargon vs plain.")
mk("synonym", "SAME", A, "aircraft fuel", "What our jets burned during the period cost more.",
   "jet fuel expense", "The reported price of powering the fleet increased.", hard=True,
   src="LUV", rat="Same fuel driver.")
mk("synonym", "SAME", T, "membership fee income", "Money earned from paid loyalty tiers grew this year.",
   "loyalty program revenue", "Subscriptions to our rewards plans brought in more.", hard=True,
   src="BBY", rat="Same paid-loyalty revenue driver.")
mk("synonym", "SAME", R, "unit growth", "The count of restaurants, net of closures, expanded.",
   "new restaurant openings", "We added locations faster than we retired them.", hard=True,
   src="CMG", rat="Same net-new-units driver.")
mk("synonym", "SAME", R, "operating margin", "Profit as a share of revenue widened over the year.",
   "return on sales", "Each dollar of revenue converted to more earnings.", hard=True,
   src="MCD", rat="Same profitability ratio, different name.")
mk("synonym", "SAME", A, "checked bag fees", "Charges travelers pay to check luggage added up.",
   "baggage fee revenue", "Income from stowed suitcase charges contributed.", hard=True,
   src="AAL ancillary", rat="Same ancillary fee driver.")
mk("synonym", "SAME", R, "gift card breakage", "Value on prepaid cards never spent flowed to income.",
   "unredeemed card income", "Balances customers left behind boosted the top line.", hard=True,
   src="DRI", rat="Same breakage income driver.")
mk("synonym", "SAME", P, "comps", "Growth at stores open a full year measured demand.",
   "comparable store sales growth", "Like-for-like locations showed how underlying demand moved.", hard=True,
   src="ORLY", rat="Abbreviation vs full metric.")
mk("synonym", "SAME", T, "e-commerce penetration", "The online share of what we sold kept rising.",
   "digital mix", "How much of the basket came through apps grew.", hard=True,
   src="BBY", rat="Same digital-share driver.")
mk("synonym", "SAME", A, "ancillary revenue", "Money beyond the base fare, from fees and extras, grew.",
   "non-ticket revenue", "Income unrelated to the seat itself contributed more.", hard=True,
   src="LUV", rat="Same non-ticket driver.")
mk("synonym", "SAME", R, "hourly labor cost", "What we pay front-line staff by the hour increased.",
   "crew wages", "Pay for the people running our kitchens went up.", hard=True,
   src="YUM", rat="Same wage driver.")
mk("synonym", "SAME", T, "occupancy expense", "The cost of keeping store space open weighed in.",
   "rent expense", "Lease charges for our retail footprint were higher.", hard=True,
   src="ULTA", rat="Same premises cost.")
mk("synonym", "SAME", R, "average restaurant sales volume", "Typical annual takings at one location edged up.",
   "AUV", "Mean yearly sales per unit improved over the period.", hard=True, pxa="restaurant", pxb="restaurant",
   src="CMG", rat="Spelled-out vs abbreviation of per-unit volume.")
mk("synonym", "SAME", A, "fuel surcharge", "An add-on fee to recover pricier fuel was applied.",
   "fuel recovery fee", "A levy offsetting higher energy cost was charged.", hard=True,
   src="cargo", rat="Same cost-recovery fee, different name.")
mk("synonym", "SAME", R, "digital sales", "Orders placed through the app and website climbed.",
   "off-premise online orders", "Purchases made online for pickup or delivery rose.", hard=True,
   src="CMG/MCD", rat="Same digital-order driver.")
mk("synonym", "SAME", P, "DIY sales", "Purchases by walk-in consumers fixing their own cars grew.",
   "retail customer sales", "Amounts from everyday shoppers at the counter rose.", hard=True,
   src="AZO/ORLY", rat="Same DIY customer segment, different label.")
mk("synonym", "SAME", A, "block hours", "Time from leaving the gate to reaching the next added up.",
   "gate-to-gate time", "The full taxi-and-fly duration per trip was tallied.", hard=True,
   src="airline ops", rat="Same time measure, named vs described.")
mk("synonym", "SAME", T, "inventory turns", "How fast stock cycled through the stores improved.",
   "inventory turnover", "The pace at which merchandise sold and refilled quickened.", hard=True,
   src="BBY", rat="Same efficiency ratio.")
mk("synonym", "SAME", R, "dine-in sales", "Meals eaten inside our restaurants brought in revenue.",
   "on-premise sales", "Consumption at the table drove part of the top line.", hard=True,
   src="CAKE/DRI", rat="Same on-premise channel, different words.")
mk("synonym", "SAME", A, "revenue per available seat mile", "Fares earned for each seat carried a mile defined the rate.",
   "unit revenue", "How much each mile of capacity brought in set the figure.", hard=True, pxa="available seat mile", pxb="available seat mile",
   src="DAL", rat="Same per-ASM revenue metric, named vs described.")
mk("synonym", "SAME", R, "franchise royalties", "A percentage of operator sales flowed to us as fees.",
   "franchise fee income", "Payments tied to licensee turnover reached our books.", hard=True,
   src="YUM/MCD", rat="Same ongoing royalty driver, different words.")
mk("synonym", "SAME", T, "advertising expense", "What we spent to promote the brand through media rose.",
   "marketing spend", "Outlays to reach shoppers with campaigns increased.", hard=True,
   src="ULTA", rat="Same promotional-spend driver.")
mk("synonym", "SAME", P, "distribution costs", "Expenses to move parts from warehouses to stores grew.",
   "logistics expense", "The cost of getting merchandise onto shelves rose.", hard=True,
   src="AZO", rat="Same supply-movement cost.")
mk("synonym", "SAME", R, "free cash flow", "Cash from operations left after building assets improved.",
   "cash generation after capex", "Operating cash net of investment in property rose.", hard=True,
   src="MCD", rat="Same free-cash-flow driver, described vs named.")
mk("synonym", "SAME", A, "on-time performance", "The share of flights arriving as scheduled improved.",
   "arrival reliability", "How often we landed on the promised minute got better.", hard=True,
   src="DAL/LUV ops", rat="Same reliability metric, different words.")
mk("synonym", "SAME", T, "conversion rate", "The share of visitors who bought something ticked up.",
   "purchase rate", "How often a browser became a buyer improved.", hard=True,
   src="BBY/ULTA", rat="Same conversion driver, different name.")
mk("synonym", "SAME", R, "beverage attachment", "How often diners added a drink to the order rose.",
   "drink incidence", "The rate of beverages sold alongside meals climbed.", hard=True,
   src="restaurant", rat="Same attach-rate driver, different jargon.")
mk("synonym", "SAME", P, "hard parts sales", "Demand for durable components like brakes and pumps grew.",
   "failure-related sales", "Purchases driven by broken components increased.", hard=True,
   src="AZO/ORLY", rat="Same non-discretionary demand driver.")


def side(name, quote, industry, per_x, slices):
    return {"name": name, "quotes": [quote], "slice_tokens": slices, "per_x": per_x, "industry": industry, "fact_type": None}


def main():
    key_path = os.path.join(OUT_DIR, "K-pairs.v1.jsonl")
    side_path = os.path.join(OUT_DIR, "K-pairs.v1.sidecar.jsonl")
    with open(key_path, "w", encoding="utf-8") as fk, open(side_path, "w", encoding="utf-8") as fs:
        for i, d in enumerate(DATA, 1):
            pid = "kp_%04d" % i
            rec = {"pair_id": pid, "provenance": "planted", "family": d["fam"],
                   "side_a": side(d["na"], d["qa"], d["ind_a"], d["pxa"], d["sla"]),
                   "side_b": side(d["nb"], d["qb"], d["ind_b"], d["pxb"], d["slb"]),
                   "rival": None, "gold": d["gold"], "gold_rationale": d["rat"], "hard": d["hard"]}
            sidecar = {"pair_id": pid, "source_ref": d["src"], "grounding": d["grounding"],
                       "drafter_gold": d["gold"], "drafter_rationale": d["rat"], "hard": d["hard"],
                       "tell_control": d["tell"], "fable": {"status": "open", "verdict": None, "note": None}}
            fk.write(json.dumps(rec, sort_keys=True) + "\n")
            fs.write(json.dumps(sidecar, sort_keys=True) + "\n")
    print("WROTE %d records -> %s (+ sidecar)" % (len(DATA), key_path))
    fams = {}
    for d in DATA:
        if d["gold"] == "DIFFERENT":
            fams[d["fam"]] = fams.get(d["fam"], 0) + 1
    print("DIFFERENT by family:", json.dumps(fams, sort_keys=True))
    print("SAME total:", sum(1 for d in DATA if d["gold"] == "SAME"),
          "| hard SAME:", sum(1 for d in DATA if d["gold"] == "SAME" and d["hard"]))


if __name__ == "__main__":
    main()
