from django.db import models


class Batter(models.Model):
    name = models.CharField(max_length=50)
    team = models.CharField(max_length=50)
    season = models.IntegerField()
    games = models.IntegerField(default=0)
    avg = models.FloatField(default=0.0)
    hr = models.IntegerField(default=0)
    rbi = models.IntegerField(default=0)
    hits = models.IntegerField(default=0)
    ops = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-avg']
        unique_together = ('name', 'team', 'season')

    def __str__(self):
        return f"{self.name} ({self.team}) {self.season}"


class TeamStanding(models.Model):
    season = models.IntegerField()
    rank = models.IntegerField()
    team = models.CharField(max_length=50)
    games = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    win_rate = models.FloatField(default=0.0)
    game_diff = models.CharField(max_length=10, default='0')
    last10 = models.CharField(max_length=20, default='')
    streak = models.CharField(max_length=10, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['rank']
        unique_together = ('season', 'team')

    def __str__(self):
        return f"{self.rank}위 {self.team} ({self.season})"

class Pitcher(models.Model):
    name = models.CharField(max_length=50)
    team = models.CharField(max_length=50)
    season = models.IntegerField()
    games = models.IntegerField(default=0)
    era = models.FloatField(default=0.0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    strikeouts = models.IntegerField(default=0)
    whip = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['era']
        unique_together = ('name', 'team', 'season')

    def __str__(self):
        return f"{self.name} ({self.team}) {self.season}"
