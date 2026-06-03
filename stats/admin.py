from django.contrib import admin
from .models import Batter, Pitcher, TeamStanding


@admin.register(Batter)
class BatterAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'season', 'games', 'avg', 'hr', 'rbi', 'ops')
    list_filter = ('season', 'team')
    search_fields = ('name',)
    ordering = ('-season', '-avg')


@admin.register(Pitcher)
class PitcherAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'season', 'games', 'era', 'wins', 'losses', 'saves', 'strikeouts', 'whip')
    list_filter = ('season', 'team')
    search_fields = ('name',)
    ordering = ('-season', 'era')


@admin.register(TeamStanding)
class TeamStandingAdmin(admin.ModelAdmin):
    list_display = ('rank', 'team', 'season', 'games', 'wins', 'losses', 'draws', 'win_rate', 'streak')
    list_filter = ('season',)
    ordering = ('season', 'rank')
