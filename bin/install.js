#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const HOME = process.env.CHENGFENG_VIDEO_FISH_HOME || os.homedir();
const PKG_ROOT = path.resolve(__dirname, '..');
const SKILL_NAME = 'chengfeng-video-fish';
const SOURCE = path.join(PKG_ROOT, 'skills', SKILL_NAME);
const PRIMARY_SKILLS = path.join(HOME, '.claude', 'skills');
const COMPAT_SKILLS = path.join(HOME, '.codex', 'skills');
const DESTINATION = path.join(PRIMARY_SKILLS, SKILL_NAME);
const LINK = path.join(COMPAT_SKILLS, SKILL_NAME);
const CONFIG = path.join(HOME, '.chengfeng-video-fish', 'config.json');
// 改名前叫 chengfeng-videocut-fish：装的时候把旧的 Skill 备份后拿掉，旧设置拷到新位置（旧的留着）。
const OLD_NAME = 'chengfeng-videocut-fish';
const OLD_CONFIG_DIR = path.join(HOME, '.chengfeng-videocut-fish');

const log = (message = '') => process.stdout.write(`${message}\n`);
const timestamp = () => new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '-');

function copyDir(source, destination) {
  fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    if (entry.name === '__pycache__') continue;
    const from = path.join(source, entry.name);
    const to = path.join(destination, entry.name);
    if (entry.isDirectory()) copyDir(from, to);
    else fs.copyFileSync(from, to);
  }
}

function backupAndRemove(target, label) {
  if (!fs.existsSync(target) && !fs.lstatSync(target, { throwIfNoEntry: false })) return null;
  const stat = fs.lstatSync(target);
  if (stat.isSymbolicLink()) {
    fs.unlinkSync(target);
    return null;
  }
  const backupRoot = path.join(PRIMARY_SKILLS, '.backups');
  const backup = path.join(backupRoot, `${label}-${timestamp()}`);
  fs.mkdirSync(backupRoot, { recursive: true });
  if (stat.isDirectory()) copyDir(target, backup);
  else fs.copyFileSync(target, backup);
  fs.rmSync(target, { recursive: true, force: true });
  return backup;
}

function has(command, args) {
  const r = spawnSync(command, args, { stdio: 'ignore' });
  return !r.error && r.status === 0;
}

function readConfig() {
  try {
    return JSON.parse(fs.readFileSync(CONFIG, 'utf8'));
  } catch {
    return {};
  }
}

function hasKey() {
  if ((process.env.FISH_API_KEY || '').trim()) return true;
  return Boolean(String(readConfig().fish_api_key || '').trim());
}

function whisperModel() {
  const configured = readConfig().whisper_model;
  const raw = configured || '~/.cache/whisper/ggml-small.bin';
  return raw.startsWith('~') ? path.join(os.homedir(), raw.slice(1)) : raw;
}

function checkTools() {
  const python = has('python3', ['--version']);
  const ffmpeg = has('ffmpeg', ['-version']) && has('ffprobe', ['-version']);
  const whisper = has('whisper-cli', ['--help']);
  const model = fs.existsSync(whisperModel());
  const key = hasKey();
  const voice = Boolean(String(readConfig().voice_id || '').trim());
  log(`${python ? '✓' : '✗'} python3`);
  log(`${ffmpeg ? '✓' : '✗'} ffmpeg / ffprobe${ffmpeg ? '' : '  (macOS: brew install ffmpeg)'}`);
  log(`${whisper ? '✓' : '✗'} whisper-cli${whisper ? '' : '  (macOS: brew install whisper-cpp)'}`);
  log(`${model ? '✓' : '✗'} whisper model ${whisperModel()}${model ? '' : '  (curl -L -o ~/.cache/whisper/ggml-small.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin)'}`);
  log(`${key ? '✓' : '✗'} Fish Audio API key${key ? '' : `  (export FISH_API_KEY=… or put {"fish_api_key": "…"} in ${CONFIG})`}`);
  log(`${voice ? '✓' : '·'} voice_id${voice ? '' : `  (optional: put {"voice_id": "…"} in ${CONFIG}, or pass --voice each time)`}`);
  return python && ffmpeg && whisper && model && key;
}

function install() {
  if (!fs.existsSync(SOURCE)) throw new Error(`Missing packaged skill: ${SOURCE}`);
  fs.mkdirSync(PRIMARY_SKILLS, { recursive: true });
  const skillBackup = backupAndRemove(DESTINATION, SKILL_NAME);
  copyDir(SOURCE, DESTINATION);
  for (const file of ['LICENSE', 'NOTICE.md', 'CITATION.cff']) {
    fs.copyFileSync(path.join(PKG_ROOT, file), path.join(DESTINATION, file));
  }
  fs.mkdirSync(COMPAT_SKILLS, { recursive: true });
  const compatBackup = backupAndRemove(LINK, `${SKILL_NAME}-compat`);
  fs.symlinkSync(DESTINATION, LINK);
  const oldSkill = backupAndRemove(path.join(PRIMARY_SKILLS, OLD_NAME), `${OLD_NAME}-renamed`);
  backupAndRemove(path.join(COMPAT_SKILLS, OLD_NAME), `${OLD_NAME}-compat-renamed`);
  const newConfigDir = path.dirname(CONFIG);
  const movedConfig = fs.existsSync(OLD_CONFIG_DIR) && !fs.existsSync(newConfigDir);
  if (movedConfig) copyDir(OLD_CONFIG_DIR, newConfigDir);
  log(`✓ ${SKILL_NAME} installed`);
  if (oldSkill) log(`  ${OLD_NAME} is now ${SKILL_NAME}; the old copy was backed up to ${oldSkill}`);
  if (movedConfig) log(`  Settings copied from ${OLD_CONFIG_DIR} to ${newConfigDir} (the old folder is kept).`);
  log('✓ Agent Skill registered');
  if (skillBackup) log('  Existing Agent Skill backed up.');
  if (compatBackup) log('  Existing Agent registration backed up.');
  log('');
  checkTools();
  log('');
  log('Restart your Agent so the Skill list reloads.');
}

function doctor() {
  const skill = path.join(DESTINATION, 'SKILL.md');
  const notice = path.join(DESTINATION, 'NOTICE.md');
  const linkOk = fs.existsSync(LINK) && fs.lstatSync(LINK).isSymbolicLink();
  log(`${fs.existsSync(skill) ? '✓' : '✗'} Agent Skill installed`);
  log(`${fs.existsSync(notice) ? '✓' : '✗'} Attribution notice present`);
  log(`${linkOk ? '✓' : '✗'} Agent Skill registration present`);
  const tools = checkTools();
  process.exitCode = fs.existsSync(skill) && fs.existsSync(notice) && linkOk && tools ? 0 : 1;
}

function uninstall() {
  const linkBackup = backupAndRemove(LINK, `${SKILL_NAME}-compat-removed`);
  const skillBackup = backupAndRemove(DESTINATION, `${SKILL_NAME}-removed`);
  log(`✓ Removed ${SKILL_NAME}; backups are preserved.`);
  if (skillBackup) log('  Removed Agent Skill backed up.');
  if (linkBackup) log('  Removed Agent registration backed up.');
  log(`  Your key and preferences in ${path.dirname(CONFIG)} are kept.`);
}

function help() {
  log('chengfeng-video-fish');
  log('');
  log('Usage:');
  log('  npx -y github:Agentchengfeng/chengfeng-video-fish install');
  log('  npx -y github:Agentchengfeng/chengfeng-video-fish doctor');
  log('');
  log('Commands: install, doctor, uninstall, help');
  log('For test-only installs: CHENGFENG_VIDEO_FISH_HOME=/tmp/test-home');
}

function main() {
  let [command = 'install', subcommand] = process.argv.slice(2);
  if (command === 'cpm') command = subcommand || 'install';
  if (['help', '--help', '-h'].includes(command)) return help();
  if (command === 'install') return install();
  if (command === 'doctor') return doctor();
  if (command === 'uninstall') return uninstall();
  log(`Unknown command: ${command}`);
  help();
  process.exitCode = 1;
}

main();
