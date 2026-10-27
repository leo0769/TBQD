<div align="center"> 
<h1 align="center">贴吧签到助手</h1>
<img src="https://img.shields.io/github/issues/LuoSue/TiebaSignIn-1?color=green">
<img src="https://img.shields.io/github/stars/LuoSue/TiebaSignIn-1?color=yellow">
<img src="https://img.shields.io/github/forks/LuoSue/TiebaSignIn-1?color=orange">
<img src="https://img.shields.io/github/license/LuoSue/TiebaSignIn-1?color=ff69b4">
<img src="https://img.shields.io/github/languages/code-size/LuoSue/TiebaSignIn-1?color=blueviolet">
</div>

# 简介

用的是手机端的接口，签到经验更多，用户只需要填写`BDUSS`即可，使用Github Actions自动签到。

# 功能

+ 贴吧自动签到
+ 签到结果通过企业微信群机器人推送到企业微信群
+ 签到结果可通过 SMTP 发送到邮箱（与企业微信渠道可任选、可并存）

# 使用方法

## 1.fork本项目
### 必须检查的仓库设置

1. 确保 `Settings -> Actions -> General` 中 Actions 处于启用状态。`tieba.yml` 中的 `workflow-keepalive` job 已配置 `actions: write` 权限，无需授予仓库 `Read and write permissions`。

2. 确保仓库没有被 Archived（Settings -> General -> Danger Zone: Archive repository）。

## 2.获取BDUSS

在网页中登录上贴吧，然后按下`F12`打开调试模式，在`cookie`中找到`BDUSS`，并复制其`Value`值。

![](./assets/获取BDUSS.gif)

## 3.将BDUSS添加到仓库的Secrets中

Name | Value
-|-
BDUSS | xxxxxxxxxxx

将上一步骤获取到的`BDUSS`粘贴到`Secrets`中

![](./assets/添加BDUSS.gif)

## 4.将WECHAT_WEBHOOK_KEY添加到仓库的Secrets中

Name | Value
-|-
WECHAT_WEBHOOK_KEY | 企业微信群机器人 Webhook 地址里 key= 后面那一段

在你 fork 的仓库 Settings → Secrets and variables → Actions → New repository secret 加一条

## 5.将邮件通知配置添加到仓库的Secrets中（可选）

不需要邮件通知可以跳过本节，不配置时脚本照常运行，只输出运行日志。

Name | Value
-|-
MAIL_HOST | SMTP 服务器地址，如 `smtp.qq.com`、`smtp.163.com`
MAIL_PORT | SMTP 端口，`465`（SSL）或 `587`（STARTTLS），留空默认 `465`
MAIL_USER | 发件邮箱地址
MAIL_PASS | 邮箱**授权码**（不是登录密码）
MAIL_TO | 收件人，多个用英文逗号分隔；留空则发给自己

> QQ 邮箱：设置 → 账户 → 开启「POP3/IMAP/SMTP 服务」后获取授权码；163 邮箱：设置 → POP3/SMTP/IMAP 中开启并获取授权码。

配置完成后，每次签到会额外发一封 HTML 邮件，主题形如 `贴吧签到结果（成功 42 / 失败 0） 2026-10-27`，正文与推送到企业微信的内容一致。企业微信与邮件两种渠道互不影响，任一发送失败都不会中断签到主流程。

## 6.开启actions

默认`actions`是处于禁止的状态，需要手动开启。

![](./assets/开启actions.gif)

## 7.第一次运行actions

+ 自己提交一次`push`。

将`run.txt`中的`flag`由`0`改为`1`

```patch
- flag: 0
+ flag: 1
```

![](./assets/运行结果.gif)

## 成功了

每天早上6:30将会自动进行签到。如果配置了 WECHAT_WEBHOOK_KEY，签到结果会推送到对应的企业微信群；如果配置了 MAIL_* 系列变量，签到结果还会同时发到你的邮箱。tieba.yml 中的 workflow-keepalive job 会自动保持该定时工作流处于启用状态。

## 2026-10-27

+ 新增邮件通知渠道（SMTP），签到结果可同时推送到企业微信与邮箱，两者可任选或并存
+ 通知逻辑收敛为 `notify_all()`，企业微信与邮件互不阻塞，单个渠道异常不影响签到主流程

## 2026-9-11

+ 增加了推送签到结果到企业微信群机器人功能

## 2026-5-30

+ 代码重构

+ 修改 API 以及签到策略

## 2020-11-01

+ 代码重构

+ 修改签到策略

大大提高一次运行，贴吧签到的成功率，基本很少的贴吧会签到失败。

+ 去除多用户的支持

+ 增加支持server酱推送，可以推送至微信

## 2020-10-19

~~增加支持多账户签到，每个账号的`BDUSS`使用`&&`分割，具体格式如下。~~
