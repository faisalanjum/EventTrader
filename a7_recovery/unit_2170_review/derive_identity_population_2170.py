"""Close the two clauses' affected population over EVERY served record identity.

The 2169 review proved its 18 selected baseline questions; it did not prove the
other 408, because its baseline frontier was found with five quote substrings
and a claim that matched none was silently skipped. This supplement removes
that hole:

  * it enumerates every distinct produced-record identity the SELECTED evidence
    actually puts in front of a grader - each asked record plus, for G3, the
    comparator records of the corrective rendering the current native score
    uses - and refuses unless every one of them lands on a reviewed claim;
  * it carries ONE temporal reading per distinct claim, keyed by the exact
    (source_id, sha256(quote)) pair rather than by a substring, and refuses
    unless the table covers the claims exactly;
  * it decides each record from what the SOURCE states, never from whether the
    produced record happens to leave comparison_baseline null.

Scope readings are reused unchanged from the published 2169 review.

    python3 -B derive_identity_population_2170.py <out.json>
"""
import collections
import hashlib
import io
import json
import os
import sys

A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery'
REVIEW_2169 = os.path.join(A7, 'unit_2169_review',
                           'derive_affected_population_2169.py')
REVIEW_2169_SHA256 = ('2d1902a370163f2198e5112005a0570c'
                      '489292660f0cc107814a9687e7ecc9a1')

#: The served surface whose judgments the current native score uses. G3 is
#: corrective-only (the original G3 contract serves neither clause); G2 carries
#: both clauses in both renderings, so its frontier is surface-independent.
SELECTED_G3_SURFACE = 'corrective'

#: ONE temporal reading per distinct served claim, keyed by exact identity.
#: Category meaning, read off the two instruction texts and NOT off any record:
#:   none                    - the source states no prior-year or sequential
#:                             comparison for this claim
#:   prior_year              - only a prior-year comparison is stated
#:   sequential_period       - only a sequential comparison is stated
#:   both:prior_year         - both are stated and the source's HEADLINE is the
#:                             prior-year one
#:   both:sequential_period  - both are stated and the source's HEADLINE is the
#:                             sequential one
#:   both:undetermined       - both are stated and the headline is not decidable
#: The served text picks prior_year whenever BOTH are stated; the corrected text
#: picks the headline and uses prior_year only to break a tie. The two therefore
#: differ on exactly one category - both:sequential_period - and are unsettled
#: on both:undetermined. Every other category leaves the required primary
#: baseline identical under either text.
TEMPORAL = (
    ('0000006201-26-000031', '6be90707d70604c2324d75e6d380ce29', 'prior_year', '18.57 17.41 6.6 %'),  # 000 Domestic (1) Revenue passenger miles (millions) 39,167 37,69
    ('0000006201-26-000031', 'd883de9c3ae4e9dec47603bcad8c3f11', 'prior_year', '32,500 30,700 5.9 %'),  # 001 Full-time equivalent employees at end of period: Mainline 10
    ('0000006201-26-000031', '91b4167dc9e71b286f2f6bc64cf8b642', 'both:prior_year', 'headline "7.6% higher year over year"; also "improving sequentially each month"'),  # 002 Total unit revenue was 7.6% higher year over year, improving
    ('0000006201-26-000031', '594b0005c313441b7889e1f19662c93c', 'none', ''),  # 003 a greater than $4 billion increase in expense related to hig
    ('0000006201-26-000032', 'fd1b603a290471894ce45c367ef20d6e', 'prior_year', '(94) (175) (81) (46.7)'),  # 004 (In millions, except percentage changes) Passenger revenue $
    ('0000006201-26-000032', 'e140b36433db532bd98ce67563000b48', 'prior_year', '$ (327) $ (530) $ (203) (38.2)'),  # 005 (In millions, except percentage changes) Passenger revenue $
    ('0000006201-26-000032', 'e42366f8f2d595320f6518e5590117a5', 'prior_year', 'an increase of 5.2% from 14.54 cents in the first quarter of 2025'),  # 006 Our 2026 first quarter CASM excluding net special items, fue
    ('0000006201-26-000032', '25640640ee9d7d12c4c5926af42dd12d', 'prior_year', 'subsequent to the first quarter of 2025'),  # 007 a 3.9% increase in mainline full-time equivalent employees s
    ('0000027904-26-000013', 'dd15eab89335df3848b1c41b394711db', 'prior_year', '(in millions) 2025 2024'),  # 008 (in millions) 2025 2024 Interest expense, net $ (679) $ (747
    ('0000027904-26-000013', 'e88ea92b1f513e5bfb81aeb46f09a9a9', 'none', ''),  # 009 Excluding the mark-to-market results, we project our annual
    ('0000027904-26-000013', '3070b2beeda2269964b61f699efa8e9a', 'prior_year', 'increased 2.4% to 13.86 cents compared to 2024; the co-stated "long-term target" is a guidance basis, not a sequential one'),  # 010 Non-fuel unit costs ("CASM-Ex", a non-GAAP financial measure
    ('0000027904-26-000013', '960828418a84e69af6fbed05fb372bdb', 'prior_year', 'a decrease of $212 million compared to 2024'),  # 011 operating income, adjusted (a non-GAAP financial measure) wa
    ('0000027904-26-000013', '983edc1a3f2fd8c1caa6d09ad3e21e1a', 'none', ''),  # 012 we currently own an approximately 19% equity stake in Grupo
    ('0000027904-26-000013', 'd9e9b7f47da3a5bf1b93ec991bbeda8b', 'none', ''),  # 013 with an option to purchase up to an additional 30 of the sam
    ('0000027904-26-000020', '1791c0a15fed4fbdc0a62efcaf663b3f', 'both:sequential_period', 'the ONLY stated change column is "1Q26 vs 4Q25 $ Change"; a "March 31, 2025" prior-year column is also present'),  # 014 (in millions) March 31, 2026 December 31, 2025 March 31, 202
    ('0000027904-26-000020', 'f32bf0eac30f786750e06ef327abcbdd', 'prior_year', 'over the same period last year'),  # 015 March quarter total revenue increased 9.4 percent over the s
    ('0000027904-26-000020', '23344ec2b69a3bb9f691fed16b31cf13', 'none', ''),  # 016 Operating Margin 6% - 8%
    ('0000027904-26-000020', '2cdd488b0c0ef65ed961a1e3c3ad0a75', 'none', ''),  # 017 Pre-tax loss of $214 million with a pre-tax margin of (1.4)
    ('0000027904-26-000020', '2cff6d4a01d7cacd6463e45a15d99246', 'none', ''),  # 018 Recent corporate survey results indicate 85 percent of respo
    ('0000027904-26-000022', '2ee8b04fe89bafaa28df063a7ad732dd', 'prior_year', 'Atlantic 1,517 11 %'),  # 019 Atlantic 1,517 11 %
    ('0000027904-26-000022', '80571d5dafb4ebe7d3eb2a2b9b66f9b5', 'prior_year', 'in the March 2026 quarter compared to a loss of $1 million in the March 2025 quarter'),  # 020 The refinery generated an operating loss of $39 million in t
    ('0000027904-26-000022', '3aea0d128e91a2f9aab85e9f08fa7c8a', 'prior_year', 'compared to the March 2025 quarter'),  # 021 Total revenue, adjusted (a non-GAAP financial measure, which
    ('0000063908-26-000032', '48620721871ed1f298b6ad36e0c8ab7d', 'none', ''),  # 022 Results included pre-tax charges of $80 million primarily re
    ('0000063908-26-000032', '64f6067756c55331267845c406e86034', 'prior_year', 'U.S. increased 6.8%'),  # 023 U.S. increased 6.8%
    ('0000092380-26-000044', 'b310fe490c6f966d81e74c7e02f1b6b8', 'prior_year', 'Three months ended March 31, 2026 2025 Percent Change'),  # 024 (in millions, except per share amounts) (unaudited) Three mo
    ('0000092380-26-000044', 'b698d58a9454c6f8049bde81800ddea1', 'prior_year', 'Three months ended March 31, 2026 2025 Percent Change'),  # 025 (in millions, except per share amounts) (unaudited) Three mo
    ('0000092380-26-000044', 'be4cefa6911f53c80493dc4733b1944d', 'none', ''),  # 026 Announced planned deployment of Starlink ultra‑fast Wi‑Fi ac
    ('0000764478-25-000057', '00a56836de9eb839c4ac7a2b9f3f49dd', 'prior_year', 'November 1, 2025 November 2, 2024 (quarter and nine-month columns, each against its own prior year)'),  # 027 ($ in millions, except per share amounts):   Three Months En
    ('0000764478-25-000057', '00ad5f7f61ebe23a25d8db9abc4c9f78', 'prior_year', 'The 7.6% comparable sales growth'),  # 028 Computing and Mobile Phones: The 7.6% comparable sales growt
    ('0000764478-25-000057', 'e771b9c67f2d31d403b1307082b6843c', 'prior_year', 'The 3.6% comparable sales growth'),  # 029 Consumer Electronics: The 3.6% comparable sales growth was d
    ('0000764478-25-000057', '106e2d23c1c93cfebb5bcdf4aa21a48e', 'prior_year', '31.8 % 31.4 % 32.1 % 31.2 %'),  # 030 Online revenue as a % of total segment revenue 31.8 % 31.4 %
    ('0000898173-26-000006', 'b7c7b6e65f4ee62bcd2f16f1b79ceec1', 'prior_year', 'December 31, 2025 / December 31, 2024'),  # 031 (In thousands, except share data) ​ ​ ​ ​ ​ ​ ​ ​ ​ ​ Decemb
    ('0000898173-26-000006', '12344e2e3b508f343aa0b9827db4b447', 'prior_year', 'versus $2.71 on 881 million shares for the same period one year ago'),  # 032 Diluted earnings per common share for the year ended Decembe
    ('0000898173-26-000006', '1d1091943305001ace3c83672eb7c318', 'none', ''),  # 033 Ending domestic store count ​ 6,447
    ('0000940944-25-000038', '768dedd4c7b89bb5612ab8da58f2045f', 'none', ''),  # 034 As of May 25, 2025, our adjusted debt to EBITDAR ratio was 2
    ('0000940944-25-000038', '99080fd4a3adc9a0fffde2f0f302e1b7', 'none', ''),  # 035 During the fourth quarter of fiscal 2025, we entered into an
    ('0000940944-25-000038', '7482418f5a7065299f17511171465858', 'prior_year', 'LongHorn Steakhouse 19.3% 18.4% 90 BP'),  # 036 LongHorn Steakhouse 19.3% 18.4% 90 BP
    ('0000940944-26-000005', '9b0399bed3bcd4500614504f1c7982a6', 'none', ''),  # 037 Reconciliation of Fiscal 2026 Reported to Adjusted Earnings
    ('0000940944-26-000005', '1855b14ecebf61bc5b13c9979426b430', 'prior_year', 'same-restaurant sales1 increase of 4.2%'),  # 038 a blended same-restaurant sales1 increase of 4.2%
    ('0000940944-26-000005', '65483e187611ceb00e1f91916d7287cc', 'prior_year', 'an increase of 5.4%'),  # 039 adjusted diluted net earnings per share from continuing oper
    ('0000940944-26-000005', 'd51bd312f67c0203ed35b5628b342f5c', 'prior_year', '% Change vs Prior Year (2.2)%'),  # 040 in millions, except per share amounts Earnings Before Income
    ('0000940944-26-000009', '593bf48cce7fb037502fb362f7bd2549', 'prior_year', 'February 22, 2026 February 23, 2025 % Chg'),  # 041 (in millions) February 22, 2026 February 23, 2025 % Chg Febr
    ('0000940944-26-000009', 'f3e888a93e56be7f2b1ff2babcc0ce69', 'prior_year', 'February 22, 2026 February 23, 2025 % Chg'),  # 042 (in millions) February 22, 2026 February 23, 2025 % Chg SRS
    ('0000940944-26-000009', '38a3acd21df73d81dc500d21b19e2894', 'prior_year', '$ 2.68 $ 2.74 (2.2)%'),  # 043 Diluted net earnings per share:   Earnings from continuing o
    ('0000940944-26-000009', '09eb182cc672d1f575da0109fb5472bf', 'none', ''),  # 044 We own and operate all of our restaurants in the United Stat
    ('0001041061-25-000109', 'd7e57f8de4f2e70751699b790fd8b554', 'none', ''),  # 045 As a result, 283 KFC and 254 Pizza Hut restaurants in Turkey
    ('0001041061-25-000109', 'c48d3c0630b995cfcd0183f1232caf19', 'none', ''),  # 046 Changes in the fair value of our ownership interest in Devya
    ('0001041061-25-000109', 'd0ba09eac7b3c9acc8b925b7fc06ac07', 'none', ''),  # 047 During the quarter ended March 31, 2024, we sold our approxi
    ('0001041061-25-000109', '2c2a1c36478d349ad5a39953684a3638', 'none', ''),  # 048 Tax (Benefit) - Tax audit in the quarter and year to date en
    ('0001041061-26-000003', '97361d4376b38e16dd1050208a329188', 'none', ''),  # 049 Fourth-quarter GAAP EPS was $1.91, and EPS excluding Special
    ('0001041061-26-000003', 'd4736ed716bfc0ca4e650312952574bf', 'none', ''),  # 050 Robust digital system sales exceeding $11 billion with digit
    ('0001041061-26-000003', 'bd01966ec2a0c37aa3ae9a77722fe50c', 'none', ''),  # 051 an acquisition of 128 Taco Bell U.S. restaurants from a fran
    ('0001041061-26-000084', '7355461fc6dbefe9dd1001bcf34c1690', 'prior_year', 'Company same-store sales growth of 5%'),  # 052 In 2025, the increase in Company sales, excluding the impact
    ('0001041061-26-000084', '73f1a4e2862cbc3ac715fd44af1d4fea', 'prior_year', 'a 6% increase from the quarterly dividend of $0.71 per share of Common Stock paid in 2025'),  # 053 In February 2026, our Board of Directors declared a quarterl
    ('0001041061-26-000084', '251cd65111939a64a6eca780595d6b6d', 'none', ''),  # 054 Other Income Tax impacts recorded as Special in the year end
    ('0001041061-26-000084', '4b4a6c3ebc4f18300216ec71568df540', 'none', ''),  # 055 The Company owned 79% of the Habit Burger & Grill units in t
    ('0001041061-26-000084', 'ede866e404a57d7db92d5d117cd1110c', 'none', ''),  # 056 The resulting net Operating Loss of $11 million for the year
    ('0001058090-26-000007', '7d99cb2a25855284faf4a48bafac5d67', 'prior_year', '2025 2024 2025 2024 (quarter and year columns, each against its own prior year)'),  # 057 (in thousands, except per share amounts) (unaudited) Three m
    ('0001058090-26-000007', '67e4484e5e61500769f497ab83356f06', 'none', ''),  # 058 350 to 370 new restaurant openings
    ('0001058090-26-000007', 'dab08bd4391ddd18a7dda4988cfab975', 'prior_year', 'remained flat at $0.25'),  # 059 Adjusted diluted earnings per share1 remained flat at $0.25
    ('0001058090-26-000007', 'dcdf7befd521220acbdc3ad9b30135b6', 'none', ''),  # 060 Chipotlanes continue to perform well and are helping enhance
    ('0001058090-26-000007', 'ab6c4686ec05b175d41067c8ecc7839e', 'prior_year', 'a decrease from 24.8%'),  # 061 Restaurant level operating margin1 was 23.4%, a decrease fro
    ('0001104659-25-102611', 'cbdc6470533c6bbfc475ee4544adbf7c', 'prior_year', 'compared to fiscal 2024 domestic commercial sales'),  # 062 Domestic commercial sales increased $329.5 million, or 6.7%,
    ('0001104659-25-102611', 'aeaf311f236e04fd528d1f9f8567f371', 'prior_year', 'Domestic commercial sales increased 6.7%'),  # 063 Domestic commercial sales increased 6.7%, which represents 3
    ('0001104659-25-102611', 'd146e63fe2edb921a1cd8a7ba07f8c40', 'none', ''),  # 064 During fiscal 2025, failure and maintenance related categori
    ('0001104659-25-102611', '01ae069c57018ab53858d66d48750145', 'prior_year', '$64.0 million charge in the current year versus $40.0 million benefit in the prior year'),  # 065 The decrease in gross margin was driven by 55 basis points (
    ('0001104659-25-102611', 'a19ca1b1d1ecc57c2157fd0cde1f8106', 'none', ''),  # 066 one individual vendor provided 13 percent of our total purch
    ('0001104659-25-105631', '17e94f089bb6b134e19b430a9f1341cb', 'prior_year', 'compared to $71.9 million for the third quarter of fiscal 2024'),  # 067 North Italia sales increased 16.1% to $83.5 million for the
    ('0001104659-25-105631', '7b90f8e58ac263e290e2900929b44d28', 'none', ''),  # 068 On October 6, 2022, we entered into a Fourth Amended and Res
    ('0001104659-25-105631', 'e5342764537e508ef8e29eec4cbffff6', 'none', ''),  # 069 We currently own and operate 366 restaurants throughout the
    ('0001104659-25-105631', '7eb3cf06982fe56b57cf8f1617962b4e', 'none', ''),  # 070 We recorded a $15.9 million loss on early debt extinguishmen
    ('0001104659-25-118458', '1ea4fafa2d0d8be8f29e3f09b256be55', 'none', ''),  # 071 Excludes 84 stores in the U.K. and Ireland operated by Space
    ('0001104659-25-118458', '90815ad138c773ff4e7974b5cffc456d', 'none', ''),  # 072 In October 2024, the Board of Directors authorized a share r
    ('0001104659-25-118458', '56e374b8806de8857dbafa536030619c', 'none', ''),  # 073 a requirement to maintain an interest coverage ratio not les
    ('0001104659-25-118458', '55a696158f7396a84fa248b563f3c0d8', 'none', ''),  # 074 borrowings bear interest, at the Company’s election, at eith
    ('0001104659-26-017090', '5efe11fc2883a8d24952addb98e2db8d', 'none', ''),  # 075 Excluding the after-tax impact of these and certain other it
    ('0001104659-26-017090', '15baa5923ef63db6645697ce16ed6463', 'prior_year', 'Comparable restaurant sales vs. prior year'),  # 076 North Italia operating information: Comparable restaurant sa
    ('0001104659-26-017090', '86d152b39509ec8c8f0554f6c338fd2a', 'none', ''),  # 077 The Company now expects to open as many as 26 new restaurant
    ('0001104659-26-027061', '6d55863997476297fba0cad7b8c4ae79', 'prior_year', 'gross profit decreased to 38.1% compared to 38.2%'),  # 078 As a percentage of net sales, gross profit decreased to 38.1
    ('0001104659-26-027061', '54f058d6d4c1a9b12ed08599623aa984', 'none', ''),  # 079 Comparable sales growth ​ ​ 2.5% to 3.5%
    ('0001104659-26-027061', '8490b47bb40a64365492ed349e7b98a4', 'none', ''),  # 080 During fiscal 2025, the Company repurchased 2.0 million shar
    ('0001104659-26-027061', 'ab92b3c9e351dc5c94e35834f0e53a1d', 'none', ''),  # 081 The following table presents the number of stores owned at t
    ('0001104659-26-032757', '4277e3e597c503c8f3e2e9a18bbc4a93', 'prior_year', 'in the comparable prior year period'),  # 082 During the second quarter of fiscal 2026, failure and mainte
    ('0001104659-26-032757', '981e378f7b5c8c7ac53e1a36bd7bf8c4', 'prior_year', 'The second quarter operating profit comparison ... in the current quarter'),  # 083 The second quarter operating profit comparison was negativel
    ('0001104659-26-032757', '4d008b1683a21e650e668dd188b44219', 'prior_year', 'an increase in total company same store sales of 3.3%'),  # 084 an increase in total company same store sales of 3.3% on a c
    ('0001104659-26-032757', 'c3d5ac44239dddb402b012b69aff378c', 'none', ''),  # 085 at February 14, 2026, operated 6,709 stores in the U.S.
    ('0001171843-26-001288', 'a822df1f94894e2a3cf8000d0bfe4255', 'prior_year', 'Domestic Same Store Sales Increase 3.4%'),  # 086 Domestic Same Store Sales Increase 3.4%
    ('0001171843-26-001288', 'add6a2a903bba022e345d59ebdf9cb90', 'none', ''),  # 087 The decrease in gross margin was driven by a 138 basis point
    ('0001171843-26-001288', '09de7a860e1ede727f1d15ae9d236636', 'none', ''),  # 088 We were also pleased to have opened 64 net new stores global
    ('AAL_2026-04-23T08.30', '204fb42dc82b9ef2df72fc33e8feec59', 'prior_year', 'up 16.7% year over year, with London up 25%'),  # 089 Atlantic unit revenue was up 16.7% year over year, with Lond
    ('AAL_2026-04-23T08.30', '999e6a7ddd89e06145b12bda8fdca060', 'none', ''),  # 090 Excluding net special items, American reported a first quart
    ('AAL_2026-04-23T08.30', '7d77bb21067aa9f5f65b61db154a28bb', 'sequential_period', 'increase sequentially up into March for double digits; the co-stated "Unit revenue of 7%" carries NO stated basis'),  # 091 Unit revenue of 7% in the quarter, and we saw it increase se
    ('AAL_2026-04-23T08.30', 'eb29969af916028b16e3d0c5449d777a', 'none', ''),  # 092 a $320 million revenue impact from winter storms
    ('AAL_2026-04-23T08.30', 'ced6cee9b76cb15ad07d8cbd3afdb24c', 'none', ''),  # 093 and then ultimately in q4 if fuel is still at the level with
    ('AAL_2026-04-23T08.30', '5a33c5d30eab2c619f392b2144587277', 'both:sequential_period', '"year over year" AND "quarter over quarter just versus the fourth quarter was up ... less than 10 percent"; only the sequential one is quantified'),  # 094 on the other revenue or the marketing component of it we did
    ('AAL_2026-04-23T08.30', 'e947920d7fb709c6a98e2e8a8fd6e48c', 'prior_year', 'our TMC performance is up 11%'),  # 095 our TMC performance is up 11% thanks to our partnerships wit
    ('CMG_2026-02-03T16.30', 'd59f738160253f1b9a94cc626c918764', 'none', ''),  # 096 For fiscal 2026, we estimate our underlying effective tax ra
    ('CMG_2026-02-03T16.30', '7b51d4c84b3d1b495e7951bd52a98b7c', 'none', ''),  # 097 G&A for the quarter was $160 million on a GAAP basis or $162
    ('CMG_2026-02-03T16.30', '1f249011db3f615a96636eb1e2c54c9d', 'prior_year', 'an increase of 38% year-over-year for that country'),  # 098 This included 21 openings in Canada, an increase of 38% year
    ('CMG_2026-02-03T16.30', '202d9f1594ca4b5ad4ee2072cc915674', 'none', ''),  # 099 Today, these two group occasions represent less than 3% of c
    ('DAL_2026-04-08T10.00', '399276c20a53856eef1ce06274028a8a', 'none', ''),  # 100 This includes an estimated $300 million benefit from our ref
    ('DAL_2026-04-08T10.00', '09c7a3c70b2fb2978ea1f1b813c5c7d9', 'prior_year', 'earnings that were 40% higher than last year'),  # 101 We delivered earnings that were 40% higher than last year
    ('DAL_2026-04-08T10.00', '291af7c82807e3bf2b6ccc80b8f0ede1', 'prior_year', 'more than doubled over the prior year'),  # 102 the MRO revenue in the first quarter more than doubled over
    ('DAL_2026-04-08T10.00', '174c26e966a9294a601d0c6b85bb0bfc', 'sequential_period', 'sequential improvement from the fourth quarter; the co-stated "growth" carries NO stated basis'),  # 103 unit revenue growth was healthy across the board with sequen
    ('DRI_2026-03-19T08.30', '5e8715fbe3ce52b6ae82133499d01e0a', 'prior_year', 'only 10 basis points below last year'),  # 104 Olive Garden delivered a strong segment profit margin of 23%
    ('DRI_2026-03-19T08.30', 'f6a89d21920dbf569a86f6bdc1dd5bd5', 'prior_year', '5.9% higher than last year'),  # 105 We generated $3.3 billion of total sales, 5.9% higher than l
    ('DRI_2026-03-19T08.30', '73100ba7a91bd125fd219363a0a159b7', 'none', ''),  # 106 adjusted diluted net earnings per share of $10.57 to $10.67
    ('DRI_2026-03-19T08.30', 'd15eb8369d5a5907a813c94ed3489fed', 'none', ''),  # 107 we've completed the exploration of strategic alternatives fo
    ('MCD_2026-02-11T16.30', '9e6ed3e473b75a81697bbb38adb7caff', 'none', ''),  # 108 We expect to open more than 1,800 restaurants in our IDL seg
    ('MCD_2026-02-11T16.30', '76f3bfdb1ef9c0e5386660c21c5a0020', 'prior_year', 'up 5.5% in constant currency for the full year'),  # 109 system-wide sales of nearly $140 billion, up 5.5% in constan
    ('MCD_2026-02-11T16.30', '567ca0649b459a03cdf49d925d6390a6', 'none', ''),  # 110 we're targeting approximately 2,600 gross restaurant opening
    ('ULTA_2026-03-12T16.30', '701592cfeda58182523ad93d6b0287af', 'prior_year', 'SG&A growth for the quarter was about 17%'),  # 111 Excluding the impact of incentive compensation and SpaceNK,
    ('ULTA_2026-03-12T16.30', '7763170e1b4b36de14db1dd9748244f6', 'prior_year', 'We grew our loyalty program by 5%'),  # 112 We grew our loyalty program by 5% to a record 46.7 million a
    ('ULTA_2026-03-12T16.30', '1503ffce5d515e46f5fed72f64f4f449', 'none', ''),  # 113 a luxury beauty retailer operating more than 80 stores in th
    ('ULTA_2026-03-12T16.30', '03145f0a3acd5a2ea28e659dc6e492a4', 'prior_year', 'representing growth between 9.4% and 11.4%'),  # 114 we anticipate diluted EPS will be between $28.05 and $28.55
    ('ULTA_2026-03-12T16.30', '2bb314ccbfc98b43c0a63fb89cf3bc37', 'none', ''),  # 115 we over delivered sales above the high end of our guidance b
    ('YUM_2026-02-04T08.15', '88521b5e75f5c4693fc750d12a296d9a', 'prior_year', 'delivered 10% divisional core operating profit growth'),  # 116 Both Taco Bell and KFC delivered 10% divisional core operati
    ('YUM_2026-02-04T08.15', 'df7566be6a5665d9af49cba9a865c1e4', 'none', ''),  # 117 In the first half, in the US, we expect approximately 250 ta
    ('YUM_2026-02-04T08.15', '8800f37ef306c4cc00f4893406285867', 'prior_year', 'core operating profit to be down approximately 15%'),  # 118 We expect Pizza Hut Q1 core operating profit to be down appr
    ('YUM_2026-02-04T08.15', '8904a25d34d6af2c5fb5b135e131a60a', 'none', ''),  # 119 reported gna of 377 million included 40 million of special e
    ('bzNews_42014391', '3d0d4317d1c2f1477ae3640b846c5214', 'none', ''),  # 120 a severe E. Coli outbreak spooked diners away
    ('bzNews_50877032', '2b733d8e9a1fb1e405828debee5e5fa9', 'none', ''),  # 121 In an official statement released by the airline on Wednesda
)

#: The published 2169 scope readings, re-keyed to the same exact claim identity.
#: An empty slice on an ACTION is what the first clause re-defines; a stated
#: part is judged the same under either text, and metric/guidance/surprise are
#: untouched by the correction.
SCOPE = {
    '0000027904-26-000013|d9e9b7f47da3a5bf1b93ec991bbeda8b': ('affected',
        'an aircraft purchase option is neither a consolidated whole-company '
        'claim nor a business population the source names, so the served text '
        'makes the empty field assert what the quote does not establish while '
        'the corrected text makes it affirmatively lawful'),
    '0000764478-25-000057|00a56836de9eb839c4ac7a2b9f3f49dd': ('open',
        'the served quote is the consolidated table, but the corrective rules '
        'send the grader to surrounding source where the impairment is '
        'attributed to Health, so whether a part is source-stated is unsettled'),
    '0000940944-26-000005|d51bd312f67c0203ed35b5628b342f5c': ('open',
        'the reconciliation footnote says primarily, not exclusively, Bahama '
        'Breeze, so whether an applicable part is source-stated - which the '
        'corrected text still requires in the field - is unsettled'),
    '0000092380-26-000044|be4cefa6911f53c80493dc4733b1944d': ('unaffected',
        'the source states the deployment is across the fleet, so whole-company '
        'scope is explicit and empty is lawful under either text'),
    '0001041061-25-000109|2c2a1c36478d349ad5a39953684a3638': ('unaffected',
        'a consolidated income-tax item; no business part is stated and the '
        'company-level reading is establishable, so both texts accept empty'),
    '0001041061-26-000084|251cd65111939a64a6eca780595d6b6d': ('unaffected',
        'a consolidated income-tax special item; no business part is stated and '
        'the company-level reading is establishable'),
    '0001058090-26-000007|7d99cb2a25855284faf4a48bafac5d67': ('unaffected',
        'a consolidated non-GAAP reconciliation of a single-brand company; no '
        'part is stated and whole-company is establishable'),
    '0001104659-25-105631|7eb3cf06982fe56b57cf8f1617962b4e': ('unaffected',
        'a corporate financing charge; no business part is stated and '
        'whole-company is establishable'),
    '0001104659-25-105631|7b90f8e58ac263e290e2900929b44d28': ('unaffected',
        'a corporate credit agreement; no business part is stated and '
        'whole-company is establishable'),
    '0001104659-26-027061|8490b47bb40a64365492ed349e7b98a4': ('unaffected',
        'the source names the consolidated Company as the actor and its own '
        'common stock as the object; empty stays lawful under either text'),
    '0001171843-26-001288|add6a2a903bba022e345d59ebdf9cb90': ('unaffected',
        'a consolidated gross-margin charge; no business part is stated and '
        'whole-company is establishable'),
    'AAL_2026-04-23T08.30|eb29969af916028b16e3d0c5449d777a': ('unaffected',
        'the stated figure is a consolidated revenue impact; no business part '
        'is stated and whole-company is establishable'),
}


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _published_2169():
    """Import the published review unchanged; refuse if its bytes moved."""
    source = io.open(REVIEW_2169, encoding='utf-8').read()
    if _sha(source) != REVIEW_2169_SHA256:
        raise ValueError('the published 2169 derivation is not at its pin')
    namespace = {'__name__': 'review_2169', '__file__': REVIEW_2169}
    exec(compile(source, REVIEW_2169, 'exec'), namespace)
    return namespace


NS = _published_2169()
CASES = NS['CASES']


def claim_key(source_id, quote):
    return '%s|%s' % (source_id, _sha(quote or '')[:32])


def identities(slots, questions):
    """Every produced-record identity the SELECTED evidence actually serves.

    An asked record is served by definition. A G3 comparator is served only in
    the rendering the score used, so the original G3 comparator rows - which
    carry neither clause anyway - are recorded separately and never scored.
    """
    facts = lambda leg, sid: CASES[leg]['answers'][sid]['facts']

    def index(leg, sid):
        """A MULTImap: a run may emit two byte-identical facts in one event,
        and silently keeping one of them would attribute a served comparator to
        an index it may not have come from."""
        table = collections.defaultdict(list)
        for at, fact in enumerate(facts(leg, sid)):
            table[json.dumps(fact, sort_keys=True)].append(at)
        return table

    served, unused, roles = {}, {}, collections.defaultdict(set)
    ambiguous = []
    for qid, renderings in slots.items():
        row = questions[qid]
        asked = (row['leg'], row['source_id'], row['produced_idx'])
        served[asked] = True
        roles[qid].add(('asked',) + asked)
        table = index(row['leg'], row['source_id'])
        for slot in renderings:
            surface = slot['source'].split(':')[0]
            for other in (slot['event'].get('other_records') or []):
                at = table.get(json.dumps(other['produced_record'], sort_keys=True))
                if not at:
                    raise ValueError('a served comparator is not a saved fact')
                if len(at) > 1:
                    # Byte-identical facts: the claim, every decision input and
                    # therefore the verdict are the same at either index, so the
                    # lowest is taken and the ambiguity is reported, not hidden.
                    ambiguous.append((qid, row['leg'], row['source_id'], at))
                identity = (row['leg'], row['source_id'], at[0])
                if surface == SELECTED_G3_SURFACE:
                    served[identity] = True
                    roles[qid].add(('comparator',) + identity)
                else:
                    unused.setdefault(identity, True)
    return sorted(served), sorted(set(unused) - set(served)), roles, ambiguous


def verdict_for(record, temporal, scope):
    """-> (verdict, clause, reason) for one served record, from the SOURCE."""
    category, evidence = temporal
    if record['fact_type'] == 'action_event' and record['item'].get('slice_parts') == []:
        if scope is None:
            raise ValueError('an empty-slice action claim has no scope reading')
        return scope[0], 'scope', scope[1]
    if category == 'both:sequential_period':
        return ('affected', 'baseline',
                'the source states a prior-year AND a sequential comparison and '
                'its headline is the sequential one (%s); the served text forces '
                'prior year, the corrected text keeps the headline' % evidence)
    if category == 'both:undetermined':
        return ('open', 'baseline',
                'the source states both comparisons and its headline is not '
                'decidable from this evidence (%s)' % evidence)
    reason = {
        'none': 'the source states no prior-year or sequential comparison for '
                'this claim, so neither text selects a temporal baseline',
        'prior_year': 'the source states only a prior-year comparison (%s), so '
                      'the served both-stated tiebreak cannot fire and the '
                      'corrected headline is that same comparison',
        'sequential_period': 'the source states only a sequential comparison '
                             '(%s), so the served both-stated tiebreak cannot '
                             'fire and the corrected headline is that same '
                             'comparison',
        'both:prior_year': 'the source states both comparisons and its headline '
                           'is the prior-year one (%s), which is what BOTH texts '
                           'select',
    }[category]
    return 'unaffected', 'baseline', (reason % evidence if '%s' in reason else reason)


def main(out):
    slots = NS['load']()
    questions = {row['question_id']: row for row in NS['build']()}
    served, unused, roles, ambiguous = identities(slots, questions)

    temporal = {}
    for source_id, quote_sha, category, evidence in TEMPORAL:
        key = '%s|%s' % (source_id, quote_sha)
        if key in temporal:
            raise ValueError('the temporal table repeats %s' % key)
        temporal[key] = (category, evidence)

    facts = lambda leg, sid, at: CASES[leg]['answers'][sid]['facts'][at]
    records, reviewed = {}, set()
    for leg, source_id, at in served:
        record = facts(leg, source_id, at)
        key = claim_key(source_id, record['item'].get('quote'))
        if key not in temporal:
            raise ValueError('no temporal reading for served claim %s' % key)
        reviewed.add(key)
        verdict, clause, reason = verdict_for(
            record, temporal[key], SCOPE.get(key))
        records['%s|%s|%d' % (leg, source_id, at)] = collections.OrderedDict([
            ('leg', leg), ('source_id', source_id), ('produced_idx', at),
            ('claim', key), ('fact_type', record['fact_type']),
            ('driver_name', record['item'].get('driver_name')),
            ('served_comparison_baseline', record['item'].get('comparison_baseline')),
            ('served_slice_parts', record['item'].get('slice_parts')),
            ('temporal_category', temporal[key][0]),
            ('clause', clause), ('verdict', verdict), ('reason', reason)])
    extra = set(temporal) - reviewed
    if extra:
        raise ValueError('the temporal table reviews %d claims nothing serves: %s'
                         % (len(extra), sorted(extra)[:3]))
    for key in SCOPE:
        if key not in reviewed:
            raise ValueError('a scope reading covers an unserved claim: %s' % key)

    order = {'affected': 0, 'open': 1, 'unaffected': 2}
    inventory = collections.OrderedDict()
    for qid in sorted(roles):
        row = questions[qid]
        hits = []
        for role, leg, source_id, at in sorted(roles[qid]):
            got = records['%s|%s|%d' % (leg, source_id, at)]
            if got['verdict'] == 'unaffected':
                continue
            hits.append(dict(got, role=role))
        verdict = 'unaffected'
        if hits:
            best = min(order[h['verdict']] for h in hits)
            verdict = ['affected', 'open'][best]
            # A claim reached ONLY as a comparator cannot be shown to move the
            # asked record's own bucket, so it lands open rather than affected.
            if verdict == 'affected' and all(
                    h['role'] == 'comparator' for h in hits
                    if h['verdict'] == 'affected'):
                verdict = 'open'
        inventory[qid] = collections.OrderedDict([
            ('kind', row['kind']), ('leg', row['leg']),
            ('source_id', row['source_id']), ('gold_idx', row['gold_idx']),
            ('produced_idx', row['produced_idx']),
            ('verdict', verdict), ('drivers', hits)])

    by_kind = collections.Counter((v['kind'], v['verdict'])
                                  for v in inventory.values())
    by_clause = collections.Counter(
        (r['clause'], r['verdict']) for r in records.values())
    categories = collections.Counter(c for _s, _q, c, _e in TEMPORAL)
    json.dump(collections.OrderedDict([
        ('schema', 'a7-two-clause-identity-population/2170'),
        ('supersedes', 'unit_2169_review/AFFECTED_POPULATION_2169.json'),
        ('selected_g3_surface', SELECTED_G3_SURFACE),
        ('counts', collections.OrderedDict([
            ('questions', len(inventory)),
            ('served_record_identities', len(records)),
            ('served_claims', len(reviewed)),
            ('identities_only_in_the_unused_original_g3_surface', len(unused)),
            ('comparators_matching_two_identical_saved_facts', len(ambiguous)),
            ('temporal_categories', dict(categories)),
            ('question_verdicts', {'%s|%s' % k: v
                                   for k, v in sorted(by_kind.items())}),
            ('record_verdicts_by_clause', {'%s|%s' % k: v
                                           for k, v in sorted(by_clause.items())}),
        ])),
        ('records', records),
        ('questions', inventory),
        ('unused_original_g3_identities', ['%s|%s|%d' % i for i in unused]),
        ('ambiguous_comparator_matches', [
            {'question_id': q, 'leg': leg, 'source_id': sid, 'candidate_idxs': at}
            for q, leg, sid, at in ambiguous]),
    ]), io.open(out, 'w', encoding='utf-8'), indent=1)
    print('questions', len(inventory), dict(by_kind))
    print('records', len(records), dict(by_clause))
    print('claims reviewed', len(reviewed), dict(categories))
    print('unused original-G3-only identities', len(unused))
    print('ambiguous comparator matches', len(ambiguous))


if __name__ == '__main__':
    main(sys.argv[1])
