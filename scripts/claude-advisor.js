export const meta = {
  name: 'claude-advisor-v2',
  description: '组合顾问：Claude Code 数据收集+诊断+保存',
  phases: [
    { title: '收集数据' },
    { title: '分析+保存' },
  ],
}

phase('收集数据')

await agent({
  label: 'collect',
  prompt: '在 /Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn 目录下执行以下3个Python命令:\n\n' +
    '命令1: PYTHONPATH=. .venv/bin/python -c "import asyncio,json;from app.core.database import init_database;from app.services.portfolio_service import PortfolioService;async def r():await init_database();s=await PortfolioService().get_portfolio_summary(\'6a094caea814b57d3357fa0b\');json.dump(s,open(\'/tmp/pf.json\',\'w\'),ensure_ascii=False,default=str);print(\'POSITIONS \'+str(len(s.get(\'positions\',[]))));asyncio.run(r())"\n\n' +
    '命令2: PYTHONPATH=. .venv/bin/python -c "import asyncio,json;from app.core.database import init_database,get_mongo_db;async def r():await init_database();db=get_mongo_db();r=await db[\'analysis_reports\'].find({\'status\':\'completed\',\'report_type\':{\'$ne\':\'portfolio\'}}).sort(\'created_at\',-1).to_list(50);json.dump([{\'code\':x.get(\'stock_symbol\')or\'\',\'recommendation\':str(x.get(\'recommendation\',\'\'))[:200]} for x in r],open(\'/tmp/t1.json\',\'w\'),ensure_ascii=False);print(\'TIER1 \'+str(len(r)));asyncio.run(r())"\n\n' +
    '命令3: PYTHONPATH=. .venv/bin/python -c "import asyncio,json;from app.core.database import init_database;from app.services.portfolio_service import PortfolioService;from app.services.exposure_service import ExposureService;async def r():await init_database();s=await PortfolioService().get_portfolio_summary(\'6a094caea814b57d3357fa0b\');m=await ExposureService().compute(s);json.dump({\'exposures\':[{\'code\':e.code,\'total\':e.total_weight} for e in (m.stock_exposures if m else [])]},open(\'/tmp/ex.json\',\'w\'),ensure_ascii=False,default=str);print(\'EXPOSURE \'+str(len(m.stock_exposures if m else [])));asyncio.run(r())"\n\n报告每个命令的输出。'
})

phase('分析+保存')

await agent({
  label: 'analyze-and-save',
  prompt: '读取 /tmp/pf.json, /tmp/t1.json, /tmp/ex.json 三个文件。\n\n' +
    '用户持仓36只约60万资产，现金32万(53%)。\n\n' +
    '你的任务：\n' +
    '1. 看Tier1报告中每个标的的 recommendation，标记矛盾\n' +
    '2. 看exposure.json中的敞口穿透，指出被基金重复暴露的标的\n' +
    '3. 输出完整的36条处方JSON（每只持仓都要有action）\n\n' +
    '格式要求：在文末输出一个```json 代码块，包含完整的处方JSON数组。\n' +
    '每条包含: code, name, action(buy/sell/hold/add/reduce/new_position), current_weight, target_weight, reasoning, priority\n\n' +
    '输出后保存到/tmp/final_presc.json，再运行:\n' +
    'cd /Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn && PYTHONPATH=. .venv/bin/python -c "\n' +
    'import asyncio, uuid, json\n' +
    'from datetime import datetime\n' +
    'from app.core.database import init_database, get_mongo_db\n' +
    'async def r():\n' +
    '  await init_database()\n' +
    '  db = get_mongo_db()\n' +
    '  with open(\'/tmp/pf.json\') as f: s = json.load(f)\n' +
    '  with open(\'/tmp/final_presc.json\') as f: presc = json.load(f)\n' +
    '  aid = str(uuid.uuid4())\n' +
    '  now = datetime.utcnow().isoformat()\n' +
    '  doc = {"advice_id":aid,"user_id":"6a094caea814b57d3357fa0b","status":"COMPLETED","created_at":now,"completed_at":now,"cio_verdict":"Claude Code v2","prescription":presc,"elapsed_seconds":0,"source":"claude-code-v2"}\n' +
    "  await db['portfolio_advice'].insert_one(doc)\n" +
    "  print('OK: ' + aid + ' rx=' + str(len(presc)))\n" +
    'asyncio.run(r())\n"\n\n' +
    '报告保存结果。保存成功后验证：\n' +
    'cd /Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn && PYTHONPATH=. .venv/bin/python -c "import asyncio;from app.core.database import init_database,get_mongo_db;async def r():await init_database();db=get_mongo_db();a=await db[\'portfolio_advice\'].find_one({\'source\':\'claude-code-v2\'},sort=[(\'created_at\',-1)]);print(\'VERIFIED: \'+a[\'advice_id\']+\' rx=\'+str(len(a.get(\'prescription\',[]))));asyncio.run(r())"'
})
