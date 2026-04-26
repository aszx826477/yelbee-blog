---
title: Gravator头像又被墙了。。。
date: 2024-09-26 11:42:00
---

之前在国内访问Gravatar源经常被墙，所以就更换了一些国内的代理源

- Gravatar 官方的 secure 源：https://secure.gravatar.com/avatar/
- Gravatar 官方的 cn 源：https://cn.gravatar.com/avatar/
- Gravatar 官方的 www 源：https://www.gravatar.com/avatar/
- V2EX：https://cdn.v2ex.com/gravatar/
- 极客族：https://sdn.geekzu.org/avatar/
- loli：https://gravatar.loli.net/avatar/

<!--more-->

有一段时间换成极客族的源是没有问题的，可是最近发现这些源全部都不通了（这个长城防火墙就不能消停一下么@(狂汗)），评论区很多头像又疯狂转圈圈，刷不出来了，今天在网上搜索之后有个国内完美的替代方案，就是**Cravatar**（看来我又落伍了呀@(黑线)，看论坛还是2023年上线的）


Gravatar官方地址

- https://cravatar.cn
- https://cravatar.com/developer/introduction



Cravatar是lifepress团队在国内做的一个公益项目，支持100%兼容Gravatar的头像API，支持三级匹配，优先匹配Cravator的头像，如果没找到则前往Gravatar查找，Gravatar查到不到还可以从QQ头像查找。


我是使用的博客引擎是typecho，接入方法比较简单，在博客程序的站点根目录，在`config.inc.php`添加如下代码即可：


```javascript

define('__TYPECHO_GRAVATAR_PREFIX__', 'https://cravatar.cn/avatar/');

```
