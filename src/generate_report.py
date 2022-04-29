import os, sys
from tabnanny import verbose
import pandas as pd, numpy as np, jinja2, pdfkit
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

class Report:

    def __init__(self, date_str) -> None:
        """
        Initializing Function

        Parameters
        ----------
        date_str : str
            specifies date in form "%m%d%Y"

        Creates
        -------
        data : DataFrame
            raw data
        date : datetime.date
            report date
        previous_data : DataFrame
            raw data from the previous report
        previous_date : datetime.date
            previous report date
        """
        self.data = pd.read_excel(f"~/Documents/volleyball/data/pickup_stats_{date_str}.xlsx", parse_dates=['date'])
        self.data.dropna(subset=['date'], inplace=True)
        self.date = datetime.strptime(date_str, '%m%d%Y').date()
        previous_file_date = datetime(2000, 1, 1).date()
        for file in os.listdir('/Users/hagenfritz/Documents/volleyball/data/'):
            str_from_file = file.split('_')[(-1)].split('.')[0]
            try:
                file_date = datetime.strptime(str_from_file, '%m%d%Y').date()
                if file_date < self.date:
                    if file_date > previous_file_date:
                        previous_file_date = file_date
            except ValueError:
                pass

        else:
            self.previous_date = previous_file_date
            previous_date_str = datetime.strftime(previous_file_date, '%m%d%Y')
            self.previous_data = pd.read_excel(f"~/Documents/volleyball/data/pickup_stats_{previous_date_str}.xlsx", parse_dates=['date'])
            self.previous_data.dropna(subset=['date'], inplace=True)
            n_games_per_player = self.data.groupby('name').count()
            single_game_players = []
            for player in n_games_per_player.index:
                if n_games_per_player.loc[(player, 'win_loss')] == 1:
                    single_game_players.append(player)
                print('Removing the following players since they only have one game:')
                for player in single_game_players:
                    print(f"\t{player}")
                else:
                    self.data = self.data[(~self.data['name'].isin(single_game_players))]
                    self.previous_data = self.previous_data[(~self.previous_data['name'].isin(single_game_players))]

    def calculate_win_rate(self, player, latest=True):
        """
        Calculates the win rate for the given player

        Parameters
        ----------
        player : str
            name of the player

        Returns
        -------
        win_rate : float
            person's win rate
        n_games : int
            number of games the player has participated in
        """
        if latest:
            data = self.data.copy()
        else:
            data = self.previous_data.copy()
        player = player.title()
        player_data = data[(data['name'] == player)]
        n_games = len(player_data)
        if n_games > 0:
            win_rate = round(len(player_data[(player_data['win_loss'] == 'win')]) / n_games * 100, 1)
        else:
            win_rate = 0
        return (win_rate, n_games)

    def calculate_ace_error_ratio(self, player, latest=True):
        """
        Calculates the ace:error ratio for the given player

        Parameters
        ----------
        player : str
            name of the player

        Returns
        -------
        ace2error : float
            player's ace:error ratio
        """
        if latest:
            data = self.data.copy()
        else:
            data = self.previous_data.copy()
        player = player.title()
        player_data = data[(data['name'] == player)]
        games_with_aces = player_data[(player_data['aces'] > 0)]
        games_with_aces_and_errors = games_with_aces[(games_with_aces['missed_serves'] > 0)]
        if len(games_with_aces) > 0:
            ace2error = round(np.nanmean(games_with_aces_and_errors['aces'] / games_with_aces_and_errors['missed_serves']), 1)
        else:
            ace2error = 0
        return ace2error

    def calculate_per_game_stats(self, latest=True):
        """
        Calculates stats per game

        Returns
        -------
        stats_per_game : DataFrame
            average stats per participant
        """
        if latest:
            data = self.data.copy()
        else:
            data = self.previous_data.copy()
        per_game = {[]:col for col in data.columns if col not in ('date', 'partner',
                                                                  'win_loss', 'match_id',
                                                                  'tournament') if col not in ('date',
                                                                                               'partner',
                                                                                               'win_loss',
                                                                                               'match_id',
                                                                                               'tournament')}
        for calculated_stat in ('win_rate', 'ace2error'):
            per_game[calculated_stat] = []
        else:
            per_game['n'] = []
            for player in data['name'].unique():
                player_data = data[(data['name'] == player)]
                for key in per_game.keys():
                    if key == 'name':
                        per_game[key].append(player)
                    elif key == 'win_rate':
                        win_rate, _ = self.calculate_win_rate(player, latest=latest)
                        per_game['win_rate'].append(win_rate)
                    elif key == 'ace2error':
                        ace2error = self.calculate_ace_error_ratio(player, latest=latest)
                        per_game['ace2error'].append(ace2error)
                    elif key == 'n':
                        per_game['n'].append(len(player_data))
                    elif key in ('hitting_efficiency', 'serving_percentage'):
                        per_game[key].append(round(np.nanmean(player_data[key]) * 100, 1))
                    else:
                        per_game[key].append(round(np.nanmean(player_data[key]), 1))
                else:
                    return pd.DataFrame(per_game)

    def get_winningest_team(self, min_games=2, top_teams=5):
        """
        Gets the team with the most victories

        Parameters
        ----------
        min_games : int, default 2
            minimum number of games required to include team as possibility
        top_teams : int, default 5
            maximum number of teams to include

        Return
        ------
        <res> : dict
            teams, their win percentage, and the number of games won
        """
        teams = []
        for i in range(len(self.data)):
            partners = sorted(self.data.iloc[i][['name', 'partner']].values)
            teams.append(f"{partners[0]}/{partners[1]}")
        else:
            data = self.data.copy()
            data['team'] = teams
            data['win'] = [1 if val == 'win' else 0 for val in data['win_loss']]
            grouped = data[['team', 'win']].groupby('team').mean()
            grouped['n'] = data.groupby('team').count()['win'] / 2
            grouped = grouped[(grouped['n'] >= min_games)]
            grouped.sort_values(['win', 'n'], ascending=False, inplace=True)
            res = {}
            for i in range(top_teams):
                res[grouped.index[i]] = (
                 f"{round(grouped.iloc[i]['win'] * 100, 1)}%", int(grouped.iloc[i]['n']))
            else:
                return res

    def get_simplified_results_per_player(self, latest=True):
        """
        Simplifies data into dictionary indexed by player with values of lists

        Returns
        -------
        <res> : dict
            summarized statistics per player
        """
        stats_per_game = self.calculate_per_game_stats(latest=latest)
        res = {}
        for player in stats_per_game.sort_values('name', ascending=True)['name']:
            player_values = stats_per_game[(stats_per_game['name'] == player)]
            important_stats = player_values[[col for col in player_values.columns if col not in ('name',
                                                                                                 'points_for',
                                                                                                 'points_against',
                                                                                                 'positive',
                                                                                                 'pass_rating')]]
            player_res = {}
            for variable in important_stats.columns:
                if variable in ('serving_percentage', 'hitting_efficiency', 'win_rate'):
                    percent_annot = '%'
                else:
                    percent_annot = ''
                player_res[variable.replace('_', ' ').replace('2', ':').title()] = f"{important_stats[variable].values[0]}{percent_annot}"
            else:
                res[player] = player_res

        else:
            return res

    def get_arrow(self, color, direction):
        """
        Gets the corresponding arrow
        """
        print(f"/Users/hagenfritz/Documents/volleyball/images/{color}_{direction}.png")
        return f"/Users/hagenfritz/Documents/volleyball/images/{color}_{direction}.png"

    def compare_stat(self, latest):
        """
        
        """
        

    def plot_stats_over_time(self, player):
        """
        Plots the players stats over time
        """
        data_player = self.data[(self.data['name'] == player)]
        data_player['date'] = pd.to_datetime(data_player['date'])
        data_player.sort_values(['date'], inplace=True)
        _, axes = plt.subplots(3, 2, figsize=(10, 12), sharex=True)
        variables = ['win_rate', 'hitting_efficiency', 'effectiveness', 'serving_percentage', 'serve_receive_rating', 'errors']
        limits = [[0, 100], [0, 1], [0, 20], [0, 1], [0, 3], [0, 10]]
        for variable, limit, ax in zip(variables, limits, axes.flat):
            variable_points = []

        for d in data_player['date'].unique():
            data_player_to_date = data_player[(data_player['date'] <= d)]
            if variable == 'win_rate':
                n_games = len(data_player_to_date)
                win_rate = round(len(data_player_to_date[(data_player_to_date['win_loss'] == 'win')]) / n_games * 100, 1)
                variable_points.append(win_rate)
            else:
                variable_points.append(np.mean(data_player_to_date[variable]))
        else:
            ax.plot((data_player['date'].unique()), variable_points, lw=3, color='black')
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            ax.xaxis.set_minor_locator(mdates.DayLocator(interval=7))
            ax.xaxis.set_minor_formatter(mdates.DateFormatter('%d'))
            ax.set_ylim(limit)
            ax.tick_params(axis='x', labelsize=12)
            ax.tick_params(axis='y', labelsize=14)
            ax.set_title((variable.replace('_', ' ').title()), fontsize=18)
            for loc in ('top', 'right'):
                ax.spines[loc].set_visible(False)
            else:
                plt.savefig(f"/Users/hagenfritz/Documents/volleyball/figures/{player}-stats_over_time.png")
                plt.close()

    def get_player_figure(self, player):
        """
        
        """
        return f"/Users/hagenfritz/Documents/volleyball/figures/{player}-stats_over_time.png"

    def run(self, n_top_players=5):
        """
        Gets the statistics and generates the final report

        Parameters
        ----------
        n_top_players : int, default 5
            number of players to include on the leaderboard
        """
        stats_per_game = self.calculate_per_game_stats(latest=True)
        top_results = {}
        for variable in stats_per_game.columns:
            if variable not in ('name', ):
                var_results = {}
                if variable in ('errors', ):
                    ascend = True
                else:
                    ascend = False
                top_results_per_variable = stats_per_game.sort_values(variable, ascending=ascend)[:n_top_players]
                for player, value in zip(top_results_per_variable['name'].values, top_results_per_variable[variable].values):
                    var_results[player] = value
                else:
                    top_results[variable] = var_results

            for player in stats_per_game['name'].unique():
                self.plot_stats_over_time(player)
            else:
                templateLoader = jinja2.FileSystemLoader(searchpath='/Users/hagenfritz/Documents/volleyball/templates/')
                templateEnv = jinja2.Environment(loader=templateLoader)
                func_dict = {'compare_stat':self.compare_stat, 
                 'get_player_figure':self.get_player_figure}
                TEMPLATE_FILE = 'stat_update_template.html'
                template = templateEnv.get_template(TEMPLATE_FILE)
                template.globals.update(func_dict)
                outputText = template.render(date=(self.date), previous_date=(self.previous_date), n_games=(int(len(self.data) / 4)),
                  win_rate=(top_results['win_rate']),
                  effectiveness=(top_results['effectiveness']),
                  kills=(top_results['kills']),
                  efficiency=(top_results['hitting_efficiency']),
                  aces=(top_results['aces']),
                  serving=(top_results['serving_percentage']),
                  blocks=(top_results['blocks']),
                  errors=(top_results['errors']),
                  pass_rating=(top_results['serve_receive_rating']),
                  ace2error=(top_results['ace2error']),
                  top_teams=self.get_winningest_team(top_teams=n_top_players),
                  per_player=(self.get_simplified_results_per_player()))
                html_file = open(f"/Users/hagenfritz/Documents/volleyball/reports/bollyvall_report-{self.date}.html", 'w')
                html_file.write(outputText)
                html_file.close()
                pdfkit.from_file(f"/Users/hagenfritz/Documents/volleyball/reports/bollyvall_report-{self.date}.html", f"/Users/hagenfritz/Documents/volleyball/reports/bollyvall_report-{self.date}.pdf")

if __name__ == '__main__':
    try:
        date_str = sys.argv[1]
        try:
            n_top_players = sys.argv[2]
        except IndexError:
            n_top_players = 5
        else:
            report = Report(date_str)
            report.run(n_top_players=n_top_players)
    except IndexError:
        print('Need to include valid date string')