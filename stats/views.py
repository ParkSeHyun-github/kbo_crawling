import json
import os
import subprocess
import sys
from datetime import datetime

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score

from django.conf import settings

MODEL_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
os.makedirs(MODEL_DIR, exist_ok=True)

# 프로세스 메모리 캐시 — 디스크 로드도 1회만
_mem_cache = {}


def _model_path(model_type, min_games):
    return os.path.join(MODEL_DIR, f'{model_type}_{min_games}.pkl')


def _meta_path(model_type, min_games):
    return os.path.join(MODEL_DIR, f'{model_type}_{min_games}.meta.json')


def _current_count(model_type):
    if model_type == 'batter':
        return Batter.objects.count()
    return Pitcher.objects.count()


def get_cached_model(model_type, min_games, build_fn):
    """메모리 → 디스크 → 재학습 순서로 캐시 확인"""
    count = _current_count(model_type)
    mem_key = (model_type, min_games, count)

    # 1) 메모리 캐시 (가장 빠름)
    if mem_key in _mem_cache:
        return _mem_cache[mem_key]

    mp = _model_path(model_type, min_games)
    meta_p = _meta_path(model_type, min_games)

    # 2) 디스크 캐시
    if os.path.exists(mp) and os.path.exists(meta_p):
        with open(meta_p) as f:
            meta = json.load(f)
        if meta.get('count') == count:
            result = joblib.load(mp)
            _mem_cache[mem_key] = result
            return result

    # 3) 재학습 후 디스크 + 메모리에 저장
    result = build_fn(min_games)
    if result:
        joblib.dump(result, mp, compress=3)
        with open(meta_p, 'w') as f:
            json.dump({'count': count}, f)
        _mem_cache[mem_key] = result
    return result

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Avg
from django.views.decorators.http import require_POST

from .models import Batter, Pitcher, TeamStanding

SEASONS = list(range(2026, 2014, -1))
BATTER_MIN_GAMES_DEFAULT = 30
PITCHER_MIN_GAMES_DEFAULT = 10

STATUS_FILE   = os.path.join(settings.BASE_DIR, 'crawl_status.json')
CRAWL_LOG_FILE = os.path.join(settings.BASE_DIR, 'crawl_log.json')


def read_crawl_log():
    if not os.path.exists(CRAWL_LOG_FILE):
        return {}
    with open(CRAWL_LOG_FILE, encoding='utf-8') as f:
        return json.load(f)


# ── 크롤링 상태 파일 헬퍼 ──────────────────────────────────────────

def read_status():
    if not os.path.exists(STATUS_FILE):
        return {'state': 'idle', 'message': '', 'started_at': None, 'finished_at': None}
    with open(STATUS_FILE, encoding='utf-8') as f:
        return json.load(f)


def write_status(state, message='', started_at=None, finished_at=None):
    data = read_status()
    data['state'] = state
    data['message'] = message
    if started_at:
        data['started_at'] = started_at
    if finished_at:
        data['finished_at'] = finished_at
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


# ── 크롤링 뷰 ────────────────────────────────────────────────────

@require_POST
def crawl_start(request):
    season_from = request.POST.get('season_from', '2026')
    season_to   = request.POST.get('season_to', season_from)
    status = read_status()

    if status['state'] == 'running':
        return JsonResponse({'ok': False, 'message': '이미 크롤링 중입니다.'})

    crawler_path = os.path.join(settings.BASE_DIR, 'crawler', 'kbo_crawler.py')
    python = sys.executable

    label = season_from if season_from == season_to else f'{season_from}~{season_to}'
    write_status('running', f'{label}시즌 크롤링 시작', started_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    subprocess.Popen(
        [python, crawler_path, season_from, season_to],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
    )

    return JsonResponse({'ok': True, 'message': f'{label}시즌 크롤링을 시작했습니다.'})


def crawl_status(request):
    data = read_status()
    data['log'] = read_crawl_log()
    return JsonResponse(data)


# ── 일반 뷰 ──────────────────────────────────────────────────────

def batter_list(request):
    season = int(request.GET.get('season', 2026))
    query = request.GET.get('q', '')
    min_games = int(request.GET.get('min_games', BATTER_MIN_GAMES_DEFAULT))

    batters = Batter.objects.filter(season=season, games__gte=min_games)
    if query:
        batters = batters.filter(name__icontains=query)

    total = Batter.objects.filter(season=season).count()

    return render(request, 'stats/batter_list.html', {
        'batters': batters,
        'season': season,
        'query': query,
        'seasons': SEASONS,
        'min_games': min_games,
        'total': total,
        'filtered': batters.count(),
        'crawl_status': read_status(),
    })


def pitcher_list(request):
    season = int(request.GET.get('season', 2026))
    query = request.GET.get('q', '')
    min_games = int(request.GET.get('min_games', PITCHER_MIN_GAMES_DEFAULT))

    pitchers = Pitcher.objects.filter(season=season, games__gte=min_games)
    if query:
        pitchers = pitchers.filter(name__icontains=query)

    total = Pitcher.objects.filter(season=season).count()

    return render(request, 'stats/pitcher_list.html', {
        'pitchers': pitchers,
        'season': season,
        'query': query,
        'seasons': SEASONS,
        'min_games': min_games,
        'total': total,
        'filtered': pitchers.count(),
        'crawl_status': read_status(),
    })


def standings(request):
    season = int(request.GET.get('season', 2026))
    teams = TeamStanding.objects.filter(season=season)
    return render(request, 'stats/standings.html', {
        'standings': teams,
        'season': season,
        'seasons': SEASONS,
        'crawl_status': read_status(),
    })


def batter_features(b):
    """타자 피처 벡터 — 파생 지표 포함"""
    hr_per_game    = b.hr / b.games if b.games else 0
    rbi_per_game   = b.rbi / b.games if b.games else 0
    hits_per_game  = b.hits / b.games if b.games else 0
    power_factor   = b.hr / b.hits if b.hits else 0       # 홈런/안타 비율 (장타 성향)
    games_pct      = b.games / 144                         # 출전 비율 (풀시즌 대비)
    rbi_per_hit    = b.rbi / b.hits if b.hits else 0       # 찬스 활용 지표
    return [
        b.avg, b.hr, b.rbi, b.hits, b.ops, b.games,
        hr_per_game, rbi_per_game, hits_per_game,
        power_factor, games_pct, rbi_per_hit,
    ]


def build_batter_model(min_games=30):
    """Random Forest + 파생 피처로 타자 예측 모델 학습"""
    seasons = sorted(Batter.objects.values_list('season', flat=True).distinct())
    X, y_avg, y_hr, y_rbi = [], [], [], []

    for s in seasons[:-1]:
        next_s = s + 1
        if next_s not in seasons:
            continue
        curr = {b.name: b for b in Batter.objects.filter(season=s, games__gte=min_games)}
        nxt  = {b.name: b for b in Batter.objects.filter(season=next_s, games__gte=min_games)}
        for name, b in curr.items():
            if name in nxt:
                n = nxt[name]
                X.append(batter_features(b))
                y_avg.append(n.avg)
                y_hr.append(n.hr)
                y_rbi.append(n.rbi)

    if len(X) < 10:
        return None

    X = np.array(X)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    models = {}
    scores = {}
    for target, y in [('avg', y_avg), ('hr', y_hr), ('rbi', y_rbi)]:
        m = RandomForestRegressor(n_estimators=100, max_depth=4, random_state=42, n_jobs=-1)
        m.fit(Xs, y)
        scores[target] = round(r2_score(y, m.predict(Xs)), 3)
        models[target] = m

    return {'models': models, 'scaler': scaler, 'scores': scores}


def pitcher_features(p):
    """투수 피처 벡터 생성 — 파생 지표 포함"""
    k_per_game  = p.strikeouts / p.games if p.games else 0
    win_rate    = p.wins / (p.wins + p.losses) if (p.wins + p.losses) else 0
    is_reliever = 1 if p.saves > p.wins else 0   # 세이브 > 승 이면 구원
    k_whip_ratio = p.strikeouts / (p.whip * p.games) if (p.whip and p.games) else 0
    return [
        p.era, p.whip, p.wins, p.losses, p.saves,
        p.strikeouts, p.games,
        k_per_game, win_rate, is_reliever, k_whip_ratio,
    ]


def build_pitcher_model(min_games=10):
    """선발/구원 분리 + 피처 엔지니어링 + Random Forest"""
    seasons = sorted(Pitcher.objects.values_list('season', flat=True).distinct())

    X_sp, y_era_sp, y_whip_sp, y_so_sp = [], [], [], []  # 선발
    X_rp, y_era_rp, y_whip_rp, y_so_rp = [], [], [], []  # 구원

    for s in seasons[:-1]:
        next_s = s + 1
        if next_s not in seasons:
            continue
        curr = {p.name: p for p in Pitcher.objects.filter(season=s, games__gte=min_games)}
        nxt  = {p.name: p for p in Pitcher.objects.filter(season=next_s, games__gte=min_games)}
        for name, p in curr.items():
            if name not in nxt:
                continue
            n = nxt[name]
            feats = pitcher_features(p)
            is_reliever = p.saves > p.wins
            if is_reliever:
                X_rp.append(feats); y_era_rp.append(n.era)
                y_whip_rp.append(n.whip); y_so_rp.append(n.strikeouts)
            else:
                X_sp.append(feats); y_era_sp.append(n.era)
                y_whip_sp.append(n.whip); y_so_sp.append(n.strikeouts)

    def train_group(X, y_era, y_whip, y_so, label):
        if len(X) < 5:
            return None
        X = np.array(X)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        models, scores = {}, {}
        for target, y in [('era', y_era), ('whip', y_whip), ('strikeouts', y_so)]:
            m = RandomForestRegressor(n_estimators=100, max_depth=4, random_state=42, n_jobs=-1)
            m.fit(Xs, y)
            scores[target] = round(r2_score(y, m.predict(Xs)), 3)
            models[target] = m
        return {'models': models, 'scaler': scaler, 'scores': scores, 'label': label}

    sp_result = train_group(X_sp, y_era_sp, y_whip_sp, y_so_sp, '선발')
    rp_result = train_group(X_rp, y_era_rp, y_whip_rp, y_so_rp, '구원')

    if not sp_result and not rp_result:
        return None

    # 통합 점수 (가중 평균)
    combined_scores = {}
    for key in ['era', 'whip', 'strikeouts']:
        vals = []
        if sp_result: vals.append(sp_result['scores'][key])
        if rp_result: vals.append(rp_result['scores'][key])
        combined_scores[key] = round(sum(vals) / len(vals), 3)

    return {'sp': sp_result, 'rp': rp_result, 'scores': combined_scores}


def predict(request):
    season = int(request.GET.get('season', 2026))
    min_batter_games = int(request.GET.get('min_batter_games', BATTER_MIN_GAMES_DEFAULT))
    min_pitcher_games = int(request.GET.get('min_pitcher_games', PITCHER_MIN_GAMES_DEFAULT))

    # ── 타자 예측 ──────────────────────────────────────────────────
    batter_result = get_cached_model('batter', min_batter_games, build_batter_model)
    batter_predictions = []
    batter_scores = {}

    if batter_result:
        batter_scores = batter_result['scores']
        scaler = batter_result['scaler']
        models = batter_result['models']
        current_batters = list(Batter.objects.filter(season=season, games__gte=min_batter_games))

        # 배치 예측 — predict() 1번 호출로 전체 처리
        feat_matrix = np.array([batter_features(b) for b in current_batters])
        Xs = scaler.transform(feat_matrix)
        pred_avg = models['avg'].predict(Xs)
        pred_hr  = models['hr'].predict(Xs)
        pred_rbi = models['rbi'].predict(Xs)

        for i, b in enumerate(current_batters):
            batter_predictions.append({
                'name': b.name, 'team': b.team,
                'cur_avg': round(b.avg, 3), 'cur_hr': b.hr, 'cur_rbi': b.rbi,
                'pred_avg': round(float(pred_avg[i]), 3),
                'pred_hr':  max(0, round(float(pred_hr[i]))),
                'pred_rbi': max(0, round(float(pred_rbi[i]))),
            })
        batter_predictions.sort(key=lambda x: x['pred_avg'], reverse=True)

    # ── 투수 예측 ──────────────────────────────────────────────────
    pitcher_result = get_cached_model('pitcher', min_pitcher_games, build_pitcher_model)
    pitcher_predictions = []
    pitcher_scores = {}

    if pitcher_result:
        pitcher_scores = pitcher_result['scores']
        current_pitchers = list(Pitcher.objects.filter(season=season, games__gte=min_pitcher_games))

        # 선발/구원 분리 후 각각 배치 예측
        for role_key, is_rel in [('sp', False), ('rp', True)]:
            group = pitcher_result[role_key]
            if not group:
                continue
            subset = [p for p in current_pitchers if (p.saves > p.wins) == is_rel]
            if not subset:
                continue
            feat_matrix = np.array([pitcher_features(p) for p in subset])
            Xs = group['scaler'].transform(feat_matrix)
            pred_era  = group['models']['era'].predict(Xs)
            pred_whip = group['models']['whip'].predict(Xs)
            pred_so   = group['models']['strikeouts'].predict(Xs)

            for i, p in enumerate(subset):
                pitcher_predictions.append({
                    'name': p.name, 'team': p.team,
                    'role': '구원' if is_rel else '선발',
                    'cur_era': round(p.era, 2), 'cur_whip': round(p.whip, 2), 'cur_so': p.strikeouts,
                    'pred_era':  round(max(0, float(pred_era[i])), 2),
                    'pred_whip': round(max(0, float(pred_whip[i])), 2),
                    'pred_so':   max(0, round(float(pred_so[i]))),
                })
        pitcher_predictions.sort(key=lambda x: x['pred_era'])

    return render(request, 'stats/predict.html', {
        'season': season,
        'next_season': season + 1,
        'seasons': SEASONS,
        'min_batter_games': min_batter_games,
        'min_pitcher_games': min_pitcher_games,
        'batter_predictions': batter_predictions[:30],
        'pitcher_predictions': pitcher_predictions[:30],
        'batter_scores': batter_scores,
        'pitcher_scores': pitcher_scores,
        'no_data': not batter_result and not pitcher_result,
        'crawl_status': read_status(),
    })


def charts(request):
    season = int(request.GET.get('season', 2026))
    min_batter_games = int(request.GET.get('min_batter_games', BATTER_MIN_GAMES_DEFAULT))
    min_pitcher_games = int(request.GET.get('min_pitcher_games', PITCHER_MIN_GAMES_DEFAULT))

    teams = ['LG', '삼성', 'KT', 'KIA', '한화', '롯데', 'NC', 'SSG', '두산', '키움']
    scatter_data = []
    for team in teams:
        avg = Batter.objects.filter(season=season, team=team, games__gte=min_batter_games).aggregate(v=Avg('avg'))['v']
        era = Pitcher.objects.filter(season=season, team=team, games__gte=min_pitcher_games).aggregate(v=Avg('era'))['v']
        if avg and era:
            scatter_data.append({'x': round(avg, 3), 'y': round(era, 2), 'label': team})

    top_hr = list(
        Batter.objects.filter(season=season, games__gte=min_batter_games)
        .order_by('-hr')[:10]
        .values('name', 'team', 'hr')
    )

    batters_all = Batter.objects.filter(season=season, games__gte=min_batter_games).values_list('avg', flat=True)
    hist_labels = ['~.200', '.200~.230', '.230~.260', '.260~.290', '.290~.320', '.320~.350', '.350~']
    hist_ranges = [(0, 0.200), (0.200, 0.230), (0.230, 0.260), (0.260, 0.290), (0.290, 0.320), (0.320, 0.350), (0.350, 1.0)]
    hist_data = [sum(1 for a in batters_all if lo <= a < hi) for lo, hi in hist_ranges]

    return render(request, 'stats/charts.html', {
        'season': season,
        'seasons': SEASONS,
        'min_batter_games': min_batter_games,
        'min_pitcher_games': min_pitcher_games,
        'scatter_data': json.dumps(scatter_data),
        'top_hr': json.dumps(top_hr),
        'hist_labels': json.dumps(hist_labels),
        'hist_data': json.dumps(hist_data),
        'crawl_status': read_status(),
    })
