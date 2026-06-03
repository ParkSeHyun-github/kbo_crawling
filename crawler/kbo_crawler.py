import sys
import os
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from playwright.sync_api import sync_playwright
from stats.models import Batter, Pitcher, TeamStanding

BATTER_URL  = 'https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx'
BATTER_URL2 = 'https://www.koreabaseball.com/Record/Player/HitterBasic/Basic2.aspx'
PITCHER_URL = 'https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx'

SEASON_SELECT = 'select#cphContents_cphContents_cphContents_ddlSeason_ddlSeason'
TEAM_SELECT   = 'select#cphContents_cphContents_cphContents_ddlTeam_ddlTeam'
PAGER_PREFIX  = 'a[id*="ucPager_btnNo"]'
PAGER_ID      = 'cphContents_cphContents_cphContents_ucPager_btnNo'

# key: 드롭다운 value, value: 표시 팀명
KBO_TEAMS = {
    'LG': 'LG',
    'SS': '삼성',
    'KT': 'KT',
    'HT': 'KIA',
    'HH': '한화',
    'LT': '롯데',
    'NC': 'NC',
    'SK': 'SSG',
    'OB': '두산',
    'WO': '키움',
}


def select_option(page, selector, value):
    page.select_option(selector, value)
    page.wait_for_load_state('networkidle')


def read_table(page):
    table = page.query_selector('table')
    if not table:
        return []
    result = []
    for row in table.query_selector_all('tr')[1:]:
        cols = [td.inner_text().strip() for td in row.query_selector_all('td')]
        if cols:
            result.append(cols)
    return result


def get_active_page(page):
    for a in page.query_selector_all(PAGER_PREFIX):
        if 'on' in (a.get_attribute('class') or ''):
            try:
                return int(a.inner_text().strip())
            except ValueError:
                pass
    return None


def click_page(page, num):
    btn = page.query_selector(f'a[id="{PAGER_ID}{num}"]')
    if btn:
        btn.click()
        page.wait_for_load_state('networkidle')
        return True
    return False


def collect_rows(page):
    """현재 선택된 조건으로 전체 페이지 순회"""
    all_rows = []
    current = 1
    while True:
        active = get_active_page(page)
        if active is None or active != current:
            break
        all_rows.extend(read_table(page))
        if not click_page(page, current + 1):
            break
        current += 1
    return all_rows


def fetch_all_by_team(page, url, season, teams):
    """팀별로 순회하며 전체 선수 수집 (중복 제거). teams는 {코드: 팀명} dict."""
    page.goto(url, wait_until='networkidle', timeout=30000)
    select_option(page, SEASON_SELECT, str(season))

    seen = set()
    all_rows = []

    for code, name in teams.items():
        print(f"  [{name}] 수집 중...")
        select_option(page, TEAM_SELECT, code)

        rows = collect_rows(page)
        new = 0
        for cols in rows:
            if len(cols) < 3:
                continue
            key = (cols[1], cols[2])  # (선수명, 팀명)
            if key not in seen:
                seen.add(key)
                all_rows.append(cols)
                new += 1
        print(f"    → {new}명 수집 (누적 {len(all_rows)}명)")

    return all_rows


def update_ops(season, rows):
    # Basic2 컬럼: 순위, 선수명, 팀명, AVG, BB, IBB, HBP, SO, GDP, SLG, OBP, OPS, ...
    count = 0
    for cols in rows:
        if len(cols) < 12:
            continue
        try:
            ops = float(cols[11]) if cols[11] else 0.0
            updated = Batter.objects.filter(name=cols[1], team=cols[2], season=season).update(ops=ops)
            count += updated
        except (ValueError, IndexError):
            continue
    print(f"OPS 업데이트 완료: {count}명")


def save_batters(season, rows):
    # 컬럼: 순위, 선수명, 팀명, AVG, G, PA, AB, R, H, 2B, 3B, HR, TB, RBI, SAC, SF
    count = 0
    for cols in rows:
        if len(cols) < 14:
            continue
        try:
            Batter.objects.update_or_create(
                name=cols[1], team=cols[2], season=season,
                defaults={
                    'avg':   float(cols[3]) if cols[3] else 0.0,
                    'games': int(cols[4]) if cols[4].isdigit() else 0,
                    'hits':  int(cols[8]) if cols[8].isdigit() else 0,
                    'hr':    int(cols[11]) if cols[11].isdigit() else 0,
                    'rbi':   int(cols[13]) if cols[13].isdigit() else 0,
                    'ops':   0.0,
                }
            )
            count += 1
        except (ValueError, IndexError):
            continue
    print(f"타자 {count}명 저장 완료")


def save_pitchers(season, rows):
    # 컬럼: 순위, 선수명, 팀명, ERA, G, W, L, SV, HLD, WPCT, IP, H, HR, BB, HBP, SO, R, ER, WHIP
    count = 0
    for cols in rows:
        if len(cols) < 19:
            continue
        try:
            Pitcher.objects.update_or_create(
                name=cols[1], team=cols[2], season=season,
                defaults={
                    'era':        float(cols[3]) if cols[3] else 0.0,
                    'games':      int(cols[4]) if cols[4].isdigit() else 0,
                    'wins':       int(cols[5]) if cols[5].isdigit() else 0,
                    'losses':     int(cols[6]) if cols[6].isdigit() else 0,
                    'saves':      int(cols[7]) if cols[7].isdigit() else 0,
                    'strikeouts': int(cols[15]) if cols[15].isdigit() else 0,
                    'whip':       float(cols[18]) if cols[18] else 0.0,
                }
            )
            count += 1
        except (ValueError, IndexError):
            continue
    print(f"투수 {count}명 저장 완료")


STANDING_URL = 'https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx'


def fetch_standings(pw_page, season):
    """팀 순위 페이지에서 행 데이터 수집 (DB 저장 없음)"""
    pw_page.goto(STANDING_URL, wait_until='networkidle', timeout=30000)
    try:
        pw_page.select_option(SEASON_SELECT, str(season))
        pw_page.wait_for_load_state('networkidle')
    except Exception:
        pass

    table = pw_page.query_selector('table')
    if not table:
        print("팀 순위 테이블을 찾을 수 없습니다.")
        return []

    result = []
    for row in table.query_selector_all('tr')[1:]:
        cols = [td.inner_text().strip() for td in row.query_selector_all('td')]
        if len(cols) >= 10:
            result.append(cols)
    return result


def save_standings(season, rows):
    count = 0
    for cols in rows:
        try:
            TeamStanding.objects.update_or_create(
                season=season, team=cols[1],
                defaults={
                    'rank':      int(cols[0]),
                    'games':     int(cols[2]),
                    'wins':      int(cols[3]),
                    'losses':    int(cols[4]),
                    'draws':     int(cols[5]),
                    'win_rate':  float(cols[6]),
                    'game_diff': cols[7],
                    'last10':    cols[8],
                    'streak':    cols[9],
                }
            )
            count += 1
        except (ValueError, IndexError):
            continue
    print(f"팀 순위 {count}팀 저장 완료")


def update_status(state, message):
    status_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'crawl_status.json')
    data = {}
    if os.path.exists(status_file):
        with open(status_file, encoding='utf-8') as f:
            data = json.load(f)
    data['state'] = state
    data['message'] = message
    if state == 'done':
        from datetime import datetime
        data['finished_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(status_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def fetch_season(pw_page, season):
    """playwright 안에서 수집만 담당 — DB 저장 없음"""
    update_status('running', f'[{season}] 타자 수집 중...')
    batter_rows = fetch_all_by_team(pw_page, BATTER_URL, season, KBO_TEAMS)

    update_status('running', f'[{season}] OPS 수집 중...')
    ops_rows = fetch_all_by_team(pw_page, BATTER_URL2, season, KBO_TEAMS)

    update_status('running', f'[{season}] 투수 수집 중...')
    pitcher_rows = fetch_all_by_team(pw_page, PITCHER_URL, season, KBO_TEAMS)

    update_status('running', f'[{season}] 팀 순위 수집 중...')
    standing_rows = fetch_standings(pw_page, season)

    return batter_rows, ops_rows, pitcher_rows, standing_rows


def save_season(season, batter_rows, ops_rows, pitcher_rows, standing_rows):
    """playwright 밖에서 DB 저장만 담당"""
    update_status('running', f'[{season}] DB 저장 중...')
    save_batters(season, batter_rows)
    update_ops(season, ops_rows)
    save_pitchers(season, pitcher_rows)
    save_standings(season, standing_rows)
    print(f"=== {season}시즌 완료 ===")


if __name__ == '__main__':
    import json
    args = sys.argv[1:]

    # 사용법:
    #   python kbo_crawler.py 2026          → 단일 시즌
    #   python kbo_crawler.py 2020 2026     → 범위 (2020~2026)
    if len(args) == 2:
        seasons = list(range(int(args[0]), int(args[1]) + 1))
    elif len(args) == 1:
        seasons = [int(args[0])]
    else:
        seasons = [2026]

    print(f"크롤링 시즌: {seasons}")

    try:
        all_data = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pw_page = browser.new_page()

            for i, season in enumerate(seasons, 1):
                print(f"\n[{i}/{len(seasons)}] {season}시즌 수집 시작")
                all_data[season] = fetch_season(pw_page, season)

            browser.close()

        # playwright 종료 후 DB 저장
        for season, data in all_data.items():
            save_season(season, *data)

        update_status('done', f'{seasons[0]}~{seasons[-1]}시즌 크롤링 완료')
        print("\n전체 완료!")

    except Exception as e:
        update_status('error', f'오류 발생: {e}')
        raise
