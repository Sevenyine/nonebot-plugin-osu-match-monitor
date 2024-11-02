<div align="center">
  <a href="https://v2.nonebot.dev/">
    <img src="https://v2.nonebot.dev/logo.png" width="200" height="200" alt="nonebot">
  </a>
</div>

<div align="center">

# nonebot-plugin-osu-match-monitor

**<img src="https://github.com/ppy/osu/blob/master/assets/lazer.png?raw=true" alt="osu!" height="20px" width="auto" /> NoneBot osu! 比赛监控**


<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/Sevenyine/nonebot-plugin-osu-match-monitor.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-osu-match-monitor">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-osu-match-monitor.svg" alt="pypi">
</a>
<a href="https://www.codefactor.io/repository/github/sevenyine/nonebot-plugin-osu-match-monitor">
    <img src="https://www.codefactor.io/repository/github/sevenyine/nonebot-plugin-osu-match-monitor/badge" alt="CodeFactor" /></a>

![GitHub Release](https://img.shields.io/github/v/release/Sevenyine/nonebot-plugin-osu-match-monitor)
<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">

</div>

## 介绍

Welcome to osu! <img src="https://github.com/ppy/osu/blob/master/assets/lazer.png?raw=true" alt="osu!" height="20px" width="auto" />

这是一个监控 osu! 游戏比赛并自动将比赛动态播报到 QQ 群内的插件。

## 安装

### 使用 nb-cli 安装

在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-osu-match-monitor

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-osu-match-monitor
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-osu-match-monitor
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-osu-match-monitor
</details>
</details>

## 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

| 配置项 | 必填 | 默认值 | 类型 |
|:-----:|:----:|:----:|:----:|
| osu_api_key | 是 | "" | str |
| osu_refresh_interval | 否 | 2 | int |
| osu_api_timeout | 否 | 5 | int |

### 如何获取 osu! API Key？

您需要注册一个 [osu!](https://osu.ppy.sh) 账号，随后打开[这个链接](https://osu.ppy.sh/home/account/edit#legacy-api)进行申请。

![api.png](https://github.com/Sevenyine/nonebot-plugin-osu-match-monitor/blob/resources/api.png?raw=true)

## 使用
### 指令表

在使用时，请自行添加对应的指令前缀。尖括号内的参数为必填。

| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| osu match monitor \<id\> | 群员 | 否 | 群聊+私聊 | 开始监控比赛 |
| osu match stopmonitor \<id\> | 群员 | 否 | 群聊+私聊 | 停止监控比赛 |

#### 如何获取 Match ID?

好问题。目前[官方给出的答复](https://github.com/ppy/osu-api/issues/282#issuecomment-544814577)是：

``你无法通过任何方式搜索多人游戏大厅。你应该通过使用 !mp make 创建游戏大厅来获取此类ID，或者当你加入大厅时从BanchoBot获取它。``

因此，获得ID的途径多为枚举。您可以使用工具例如 [mp finder](https://shdewz.me/tools/mpfinder/) 帮助您枚举。若您正在举行锦标赛，可以参考[这个文档](https://osu.ppy.sh/wiki/en/osu%21_tournament_client/osu%21tourney/Tournament_management_commands)。

### 效果图

![example.jpg](https://github.com/Sevenyine/nonebot-plugin-osu-match-monitor/blob/resources/example.JPG?raw=true)
