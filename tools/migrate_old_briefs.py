#!/usr/bin/env python3
"""一次性迁移：给已发布的旧简报页补上新模板的 SEO/性能/体验改进。

- 合并 JS → ../app.js?v=20261007 (defer)
- styles.css 加 ?v=20261007
- logo → webp
- 内链去 .html 后缀
- canvas 加 role="img" + aria-label（价格区间从页内 CHART_JSON 计算）
- OG/Twitter 标签 + canonical（描述用 archive_title，图片用当日走势图；旧图已清理则用站徽）
- 价格旁加「M/D 收盘」
- 分析师评级区加 MarketBeat 口径注释
"""
import glob
import html as htmlmod
import json
import os
import re

SITE = os.path.expanduser("~/workspace/avgo-site")
TOOLS = os.path.join(SITE, "tools")
V = "20261007"
SITE_URL = "https://avgo.pages.dev"


def main():
    for page in sorted(glob.glob(os.path.join(SITE, "briefs", "*.html"))):
        date = os.path.basename(page)[:10]
        with open(page, encoding="utf-8") as f:
            s = f.read()
        orig = s

        # 1. 合并后的 JS
        s = re.sub(
            r'<script src="\.\./theme\.js"></script>\s*'
            r'<script src="\.\./menu\.js"></script>\s*'
            r'<script src="\.\./header-scroll\.js"></script>\s*'
            r'<script src="\.\./charts\.js"></script>',
            '<script src="../app.js?v=%s" defer></script>' % V, s)

        # 2. CSS 版本号
        s = s.replace('<link rel="stylesheet" href="../styles.css">',
                      '<link rel="stylesheet" href="../styles.css?v=%s">' % V)

        # 3. logo webp
        s = s.replace('src="../assets/avgo-emblem.png"',
                      'src="../assets/avgo-emblem.webp"')

        # 4. 内链去后缀
        s = s.replace('href="../index.html"', 'href="../"')

        # 5. canvas aria-label（价格区间从页内图表 JSON 计算）
        m = re.search(
            r'<script type="application/json" id="avgo-data-%s">(.*?)</script>'
            % re.escape(date), s, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                closes = [c for c in data.get("close", []) if c]
                rng = "区间 $%.2f–$%.2f" % (min(closes), max(closes)) if closes else ""
            except Exception:
                rng = ""
            aria = "AVGO 近 6 个月价格走势图%s" % ("，" + rng if rng else "")
            s = s.replace(
                '<canvas class="chart" data-price="avgo-data-%s"></canvas>' % date,
                '<canvas class="chart" data-price="avgo-data-%s" role="img" aria-label="%s"></canvas>'
                % (date, htmlmod.escape(aria, quote=True)))
        s = s.replace(
            '<canvas class="chart sm" data-volume="avgo-data-%s"></canvas>' % date,
            '<canvas class="chart sm" data-volume="avgo-data-%s" role="img" aria-label="AVGO 近 6 个月成交量柱状图"></canvas>' % date)
        s = s.replace(
            '<canvas class="chart sm" data-rsi="avgo-data-%s"></canvas>' % date,
            '<canvas class="chart sm" data-rsi="avgo-data-%s" role="img" aria-label="AVGO 近 6 个月 RSI(14) 动量曲线，70 上方为超买区、30 下方为超卖区"></canvas>' % date)

        # 6. OG/Twitter + canonical
        if "og:title" not in s:
            inp = os.path.join(TOOLS, "input", date + ".json")
            archive_title = date
            if os.path.exists(inp):
                archive_title = json.load(open(inp, encoding="utf-8")).get(
                    "archive_title", date)
            pm = re.search(r'<div class="price num">\$([\d.]+)</div>', s)
            price = pm.group(1) if pm else ""
            cm = re.search(r'<div class="change (?:up|down)">([^<]+)</div>', s)
            chg = cm.group(1) if cm else ""
            chart = os.path.join(SITE, "charts", "avgo-%s.png" % date)
            og_img = (SITE_URL + "/charts/avgo-%s.png" % date
                      if os.path.exists(chart)
                      else SITE_URL + "/assets/avgo-emblem.webp")
            og_title = "AVGO 日报 %s：$%s（%s）" % (date, price, chg)
            og_desc = htmlmod.escape(archive_title, quote=True)
            head_tags = (
                '<link rel="canonical" href="%s/briefs/%s">\n'
                '<meta property="og:type" content="article">\n'
                '<meta property="og:site_name" content="AVGO 每日追踪">\n'
                '<meta property="og:title" content="%s">\n'
                '<meta property="og:description" content="%s">\n'
                '<meta property="og:url" content="%s/briefs/%s">\n'
                '<meta property="og:image" content="%s">\n'
                '<meta name="twitter:card" content="summary_large_image">\n'
                '<meta name="twitter:title" content="%s">\n'
                '<meta name="twitter:description" content="%s">\n'
                '<meta name="twitter:image" content="%s">\n'
                % (SITE_URL, date,
                   htmlmod.escape(og_title, quote=True), og_desc,
                   SITE_URL, date, og_img,
                   htmlmod.escape(og_title, quote=True), og_desc, og_img))
            s = s.replace("</title>\n",
                          "</title>\n" + head_tags, 1)

        # 7. 价格旁加「M/D 收盘」
        if "price-date" not in s:
            m = re.search(r"数据截至 (\d{4})-(\d{2})-(\d{2}) 美股收盘", s)
            if m:
                short = "%d/%d" % (int(m.group(2)), int(m.group(3)))
                s = re.sub(
                    r'(<div class="price num">\$[\d.]+</div>)',
                    r'\1\n<div class="price-date">%s 收盘</div>' % short,
                    s, count=1)

        # 8. 评级口径注释
        if "caliber-note" not in s:
            s = re.sub(
                r'(<section class="brief-section" id="ratings">.*?</ul>)(\n</section>)',
                r'\1\n<p class="caliber-note">综合评级口径：MarketBeat。如统计口径发生变更，会在此处注明。</p>\2',
                s, flags=re.DOTALL, count=1)

        if s != orig:
            with open(page, "w", encoding="utf-8") as f:
                f.write(s)
            print("migrated:", date)
        else:
            print("unchanged:", date)


if __name__ == "__main__":
    main()
