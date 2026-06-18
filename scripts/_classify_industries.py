import asyncio, json
from app.core.database import init_database, get_mongo_db

async def main():
    await init_database()
    db = get_mongo_db()

    with open('data/advisor_runs/20260606_143740/data_portfolio.json') as f:
        pf = json.load(f)
    codes = [p['code'] for p in pf['positions']]

    # check industry_classification_cache
    cache = await db['industry_classification_cache'].find({'code': {'$in': codes}}).to_list(None)
    code_to_ind = {}
    for c in cache:
        ind = c.get('bucket') or c.get('industry') or '未分类'
        code_to_ind[c['code']] = ind
    print(f"Classification cache: {len(code_to_ind)}/{len(codes)} matched")

    # Try: use the industry_coverage data from latest advice
    latest = await db['portfolio_advice'].find_one(
        {'user_id': '6a094caea814b57d3357fa0b', 'status': 'COMPLETED'},
        sort=[('created_at', -1)]
    )
    if latest:
        mi = latest.get('market_intel', {})
        inds = mi.get('industries', [])
        # build code→industry map from market_intel.industries
        for ind in inds:
            for c in ind.get('codes', []):
                if c not in code_to_ind:
                    code_to_ind[c] = ind.get('industry', '未分类')
        print(f"After market_intel merge: {len(code_to_ind)}/{len(codes)} matched")

    # Classify all positions
    industries = {}
    for p in pf['positions']:
        code = p['code']
        ind = code_to_ind.get(code, '未分类')
        if ind not in industries:
            industries[ind] = {'industry': ind, 'codes': [], 'names': [], 'total_weight': 0, 'total_value': 0}
        industries[ind]['codes'].append(code)
        industries[ind]['names'].append(p.get('name', code))
        industries[ind]['total_weight'] += p.get('weight', 0)
        industries[ind]['total_value'] += p.get('market_value_cny', 0) or 0

    for k in industries:
        industries[k]['total_weight'] = round(industries[k]['total_weight'], 1)
        industries[k]['total_value'] = round(industries[k]['total_value'], 0)

    ind_list = sorted(industries.values(), key=lambda x: -x['total_weight'])

    with open('data/advisor_runs/20260606_143740/industry_list.json', 'w') as f:
        json.dump(ind_list, f, ensure_ascii=False, indent=2)

    print(f"\nIndustry list ({len(ind_list)}):")
    for ind in ind_list:
        print(f"  {ind['industry']}: {len(ind['codes'])} codes, {ind['total_weight']:.1f}%")

asyncio.run(main())
