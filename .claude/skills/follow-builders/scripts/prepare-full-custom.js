#!/usr/bin/env node
/**
 * prepare-full-custom.js
 * 1. Runs scrape-custom-x.py (CloakBrowser) and prepare-digest.js in parallel
 * 2. Merges custom AI supply chain X feed into the standard builders feed
 * 3. Outputs combined JSON to stdout for the LLM to remix
 *
 * Usage: node prepare-full-custom.js
 * Output: combined JSON to stdout
 */

import { execFileSync } from 'child_process';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

const SCRIPT_DIR = import.meta.dirname;
const ORIGINAL_PREPARE = join(SCRIPT_DIR, 'prepare-digest.js');
const CUSTOM_SCRAPER = join(SCRIPT_DIR, 'scrape-custom-x.py');
const CUSTOM_X_JSON = join(homedir(), '.follow-builders', 'custom-feed-x.json');

function run(cmd, args, timeoutSec = 300) {
  try {
    const result = execFileSync(cmd, args, {
      encoding: 'utf-8',
      timeout: timeoutSec * 1000,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    return result;
  } catch (err) {
    console.error(`[custom] ${cmd} 执行失败: ${err.message}`);
    return null;
  }
}

function main() {
  // 1. Run scraper + standard feed in parallel
  console.error('[custom] 抓取 AI 产业链 X 账号...');
  const scraperOk = run('python3', [CUSTOM_SCRAPER], 600) !== null;

  console.error('[custom] 获取标准 Builder feeds...');
  const originalRaw = run('node', [ORIGINAL_PREPARE]);
  if (!originalRaw) {
    console.error('[custom] 标准 feed 获取失败');
    process.exit(1);
  }

  let original;
  try {
    original = JSON.parse(originalRaw);
  } catch {
    console.error('[custom] 标准 feed JSON 解析失败');
    process.exit(1);
  }

  // 2. Merge custom X feed
  if (scraperOk && existsSync(CUSTOM_X_JSON)) {
    try {
      const custom = JSON.parse(readFileSync(CUSTOM_X_JSON, 'utf-8'));
      const customX = custom.x || [];
      console.error(`[custom] 合并自定义: ${customX.length} 账号, ${custom.stats?.newTweets || 0} 新推文, ${custom.stats?.sourcesBlocked || 0} 受限`);

      if (customX.length > 0) {
        original.x = [...(original.x || []), ...customX];
        if (original.stats) {
          original.stats.xBuilders = (original.stats.xBuilders || 0) + customX.length;
          original.stats.totalTweets = (original.stats.totalTweets || 0) +
            customX.reduce((sum, a) => sum + (a.tweets?.length || 0), 0);
        }
      }
    } catch (err) {
      console.error(`[custom] 自定义 feed 合并失败: ${err.message}`);
    }
  } else {
    console.error('[custom] 无自定义 X feed，仅使用标准源');
  }

  // 3. Output merged JSON
  process.stdout.write(JSON.stringify(original));
}

main();
