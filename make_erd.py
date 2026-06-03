import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Windows 한글 폰트 설정
for fname in ['Malgun Gothic', 'NanumGothic', 'AppleGothic']:
    try:
        plt.rcParams['font.family'] = fname
        break
    except Exception:
        continue
plt.rcParams['axes.unicode_minus'] = False
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(16, 10))
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis('off')
fig.patch.set_facecolor('#f5f5f5')

def draw_table(ax, x, y, title, subtitle, fields, header_color, width=3.6):
    row_h = 0.38
    header_h = 0.6
    total_h = header_h + len(fields) * row_h + 0.15

    # 그림자
    shadow = FancyBboxPatch((x+0.06, y-total_h-0.06), width, total_h,
                             boxstyle="round,pad=0.05", linewidth=0,
                             facecolor='#cccccc', zorder=1)
    ax.add_patch(shadow)

    # 헤더
    header = FancyBboxPatch((x, y-header_h), width, header_h,
                              boxstyle="round,pad=0.0", linewidth=0,
                              facecolor=header_color, zorder=2)
    ax.add_patch(header)
    ax.text(x+0.18, y-0.22, title, fontsize=13, fontweight='bold',
            color='white', va='center', zorder=3)
    ax.text(x+0.18, y-0.46, subtitle, fontsize=8.5, color='#ffffffbb',
            va='center', zorder=3)

    # 바디
    body = FancyBboxPatch((x, y-total_h), width, total_h-header_h,
                           boxstyle="round,pad=0.0", linewidth=0,
                           facecolor='white', zorder=2)
    ax.add_patch(body)

    for i, (fname, ftype, fkind) in enumerate(fields):
        ry = y - header_h - (i+0.5)*row_h - 0.08
        # 행 배경
        if fkind == 'pk':
            row_bg = FancyBboxPatch((x, y-header_h-i*row_h-0.08), width, row_h,
                                     boxstyle="round,pad=0.0", linewidth=0,
                                     facecolor='#fff8e1', zorder=2)
            ax.add_patch(row_bg)
            icon = '🔑'
        elif fkind == 'idx':
            row_bg = FancyBboxPatch((x, y-header_h-i*row_h-0.08), width, row_h,
                                     boxstyle="round,pad=0.0", linewidth=0,
                                     facecolor='#e8f5e9', zorder=2)
            ax.add_patch(row_bg)
            icon = '◆'
        else:
            icon = ' '

        ax.text(x+0.15, ry, f"{icon} {fname}", fontsize=9,
                va='center', color='#333', zorder=3,
                fontproperties=None)
        ax.text(x+width-0.1, ry, ftype, fontsize=8,
                va='center', ha='right', color='#999', zorder=3)

        # 구분선
        ax.plot([x, x+width], [y-header_h-i*row_h-0.08, y-header_h-i*row_h-0.08],
                color='#eeeeee', linewidth=0.5, zorder=3)

    # 테두리
    border = FancyBboxPatch((x, y-total_h), width, total_h,
                              boxstyle="round,pad=0.0", linewidth=1.2,
                              edgecolor='#dddddd', facecolor='none', zorder=4)
    ax.add_patch(border)
    return y - total_h

BATTER_FIELDS = [
    ('id',         'AutoField',    'pk'),
    ('name',       'CharField(50)',''),
    ('team',       'CharField(50)','idx'),
    ('season',     'IntegerField', 'idx'),
    ('games',      'IntegerField', ''),
    ('avg',        'FloatField',   ''),
    ('hr',         'IntegerField', ''),
    ('rbi',        'IntegerField', ''),
    ('hits',       'IntegerField', ''),
    ('ops',        'FloatField',   ''),
    ('created_at', 'DateTimeField',''),
]

PITCHER_FIELDS = [
    ('id',         'AutoField',    'pk'),
    ('name',       'CharField(50)',''),
    ('team',       'CharField(50)','idx'),
    ('season',     'IntegerField', 'idx'),
    ('games',      'IntegerField', ''),
    ('era',        'FloatField',   ''),
    ('wins',       'IntegerField', ''),
    ('losses',     'IntegerField', ''),
    ('saves',      'IntegerField', ''),
    ('strikeouts', 'IntegerField', ''),
    ('whip',       'FloatField',   ''),
    ('created_at', 'DateTimeField',''),
]

STANDING_FIELDS = [
    ('id',         'AutoField',    'pk'),
    ('season',     'IntegerField', 'idx'),
    ('rank',       'IntegerField', ''),
    ('team',       'CharField(50)','idx'),
    ('games',      'IntegerField', ''),
    ('wins',       'IntegerField', ''),
    ('losses',     'IntegerField', ''),
    ('draws',      'IntegerField', ''),
    ('win_rate',   'FloatField',   ''),
    ('game_diff',  'CharField(10)',''),
    ('last10',     'CharField(20)',''),
    ('streak',     'CharField(10)',''),
    ('updated_at', 'DateTimeField',''),
]

draw_table(ax, 0.4,  9.7, 'Batter',       '타자 성적',  BATTER_FIELDS,  '#1a237e')
draw_table(ax, 6.2,  9.7, 'Pitcher',      '투수 성적',  PITCHER_FIELDS, '#1b5e20')
draw_table(ax, 12.0, 9.7, 'TeamStanding', '팀 순위',    STANDING_FIELDS,'#4a148c')

# 연결선 (논리적 관계 표시)
ax.annotate('', xy=(6.2, 5.5), xytext=(4.0, 5.5),
            arrowprops=dict(arrowstyle='<->', color='#9e9e9e', lw=1.5, linestyle='dashed'))
ax.text(5.1, 5.65, 'season / team', fontsize=8, ha='center', color='#9e9e9e')

ax.annotate('', xy=(12.0, 5.5), xytext=(9.8, 5.5),
            arrowprops=dict(arrowstyle='<->', color='#9e9e9e', lw=1.5, linestyle='dashed'))
ax.text(10.9, 5.65, 'season / team', fontsize=8, ha='center', color='#9e9e9e')

# unique_together 표기
for x, text in [(0.4, 'UNIQUE: (name, team, season)'),
                (6.2, 'UNIQUE: (name, team, season)'),
                (12.0, 'UNIQUE: (season, team)')]:
    ax.text(x+0.1, 0.55, text, fontsize=7.5, color='#888',
            style='italic')

# TeamStanding 경고
ax.text(12.1, 0.3, '⚠ KBO 공식: 현재 시즌만 제공', fontsize=8, color='#e65100')

# 범례
legend_x, legend_y = 0.4, 0.95
ax.add_patch(FancyBboxPatch((legend_x-0.1, legend_y-0.28), 5.0, 0.38,
             boxstyle="round,pad=0.05", facecolor='white',
             edgecolor='#ddd', linewidth=1, zorder=2))
for i, (color, label) in enumerate([('#fff8e1', '🔑 PK (기본키)'),
                                      ('#e8f5e9', '◆ 인덱스 / 필터 기준'),
                                      ('white',   '  일반 필드')]):
    rect = mpatches.Rectangle((legend_x + i*1.6, legend_y-0.18), 0.25, 0.22,
                               facecolor=color, edgecolor='#ccc', linewidth=0.8)
    ax.add_patch(rect)
    ax.text(legend_x + i*1.6 + 0.32, legend_y-0.07, label,
            fontsize=8, va='center', color='#555')

ax.set_title('KBO 대시보드 ERD', fontsize=16, fontweight='bold',
             color='#1a237e', pad=10)

plt.tight_layout()
plt.savefig('erd.png', dpi=150, bbox_inches='tight', facecolor='#f5f5f5')
print("erd.png 저장 완료")
