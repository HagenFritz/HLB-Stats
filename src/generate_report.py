import os, sys
import argparse

import pandas as pd, numpy as np, jinja2, pdfkit
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import logging
import pathlib

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
        # file paths
        self.path_to_this_dir = f"{pathlib.Path(__file__).resolve().parent}"
        self.project_dir = f"{pathlib.Path(__file__).resolve().parent.parent}" # taking advantage of project filesystem

        # setting up logging
        self.logger = logging.getLogger(__name__)
        log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(level=logging.INFO, filename=f'{self.path_to_this_dir}/report.log', filemode='w', format=log_fmt,datefmt='%Y/%m/%d %H:%M:%S')

        # Data
        # ----
        # getting current, specified data
        self.data = pd.read_excel(f"{self.project_dir}/data/pickup_stats_{date_str}.xlsx", parse_dates=['date'])
        self.data.dropna(subset=['date'], inplace=True)
        self.date = datetime.strptime(date_str, '%m%d%Y').date()
        self.total_games = int(len(self.data)/4)
        
        # getting previous data
        previous_file_date = datetime(2000, 1, 1).date()
        for file in os.listdir(f"{self.project_dir}/data/"): # looping through all previous files
            if file[-1] in ["v","x"]: # looking for XSLX or CSV files
                str_from_file = file.split('_')[(-1)].split('.')[0] 
                try:
                    file_date = datetime.strptime(str_from_file, '%m%d%Y').date()
                    if file_date < self.date:
                        if file_date > previous_file_date:
                            previous_file_date = file_date # updating to a later file and looking again
                        else:
                            self.previous_date = previous_file_date
                            previous_date_str = datetime.strftime(previous_file_date, '%m%d%Y')
                            self.previous_data = pd.read_excel(f"{self.project_dir}/data/pickup_stats_{previous_date_str}.xlsx", parse_dates=['date'])
                            self.previous_data.dropna(subset=['date'], inplace=True)
                except ValueError as e:
                    self.logger.exception(e)

        # Players with only a few games
        # --------------------------------------
        ## Getting the Players
        n_games_per_player = self.data.groupby('name').count()
        low_game_players = []
        for player in n_games_per_player.index:
            if n_games_per_player.loc[(player, 'win_loss')] < 0.05 * self.total_games: # have to have played in at least 5% of the games
                low_game_players.append(player)
        
        ## Logging the Low-Playing Players
        self.logger.warning('Removing the following players since they only have one game:')
        for player in low_game_players:
            self.logger.warning(f"\t{player}")

        ## Removing them from both datasets
        self.data = self.data[(~self.data['name'].isin(low_game_players))]
        self.previous_data = self.previous_data[(~self.previous_data['name'].isin(low_game_players))]

    def calculate_win_rate(self, player, latest=True):
        """
        Calculates the win rate for the given player

        Parameters
        ----------
        player : str
            name of the player
        latest : boolean, default True
            whether to use the latest data or the previous data

        Returns
        -------
        win_rate : float
            person's win rate
        n_games : int
            number of games the player has participated in
        """
        # data version control
        if latest:
            data = self.data.copy()
        else:
            data = self.previous_data.copy()

        player = player.title()
        player_data = data[(data['name'] == player)]
        n_games = len(player_data)
        if n_games > 0:
            win_rate = len(player_data[(player_data['win_loss'] == 'win')]) / n_games * 100
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
        latest : boolean, default True
            whether to use the latest data or the previous data

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
            ace2error = np.nanmean(games_with_aces_and_errors['aces'] / games_with_aces_and_errors['missed_serves'])
        else:
            ace2error = 0
        return ace2error

    def calculate_point_differential(self, player, latest=True):
        """
        Calculates the ace:error ratio for the given player

        Parameters
        ----------
        player : str
            name of the player
        latest : boolean, default True
            whether to use the latest data or the previous data

        Returns
        -------
        point_diff : float
            player's average point differential
        """
        if latest:
            data = self.data.copy()
        else:
            data = self.previous_data.copy()

        player = player.title()
        player_data = data[(data['name'] == player)]
        return np.nanmean(player_data['points_for'] / player_data['points_against'])

    def calculate_per_game_stats(self, latest=True, decimals=1):
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

        per_game = {col: [] for col in data.columns if col not in ['date', 'partner','win_loss', 'match_id','tournament',"switch1","switch2","switch3","switch4","switch5","switch6","switch7","switch8"]}
        for calculated_stat in ('n','win_rate', 'ace2error',"point_differential"):
            per_game[calculated_stat] = []

        for player in data['name'].unique():
            player_data = data[(data['name'] == player)]
            for key in per_game.keys():
                if key == 'name':
                    per_game[key].append(player)
                elif key == 'win_rate':
                    win_rate, _ = self.calculate_win_rate(player, latest=latest)
                    per_game['win_rate'].append(round(win_rate, decimals))
                elif key == 'ace2error':
                    ace2error = self.calculate_ace_error_ratio(player, latest=latest)
                    per_game['ace2error'].append(round(ace2error, decimals))
                elif key == "point_differential":
                    point_diff = self.calculate_point_differential(player, latest=latest)
                    per_game["point_differential"].append(round(point_diff, decimals))
                elif key == 'n':
                    per_game['n'].append(len(player_data))
                elif key in ('hitting_efficiency', 'serving_percentage'):
                    per_game[key].append(round(np.nanmean(player_data[key]) * 100, decimals))
                else:
                    per_game[key].append(round(np.nanmean(player_data[key]), decimals))
                    
        return pd.DataFrame(per_game)

    def get_winningest_team(self, min_games=5, top_teams=5):
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
        print(f"{self.project_dir}/images/{color}_{direction}.png")
        return f"{self.project_dir}/images/{color}_{direction}.png"

    def compare_stats(self):
        """
        
        """
        latest_stats = self.calculate_per_game_stats(latest=True,decimals=2)
        previous_stats = self.calculate_per_game_stats(latest=False,decimals=2)
        latest_stats.set_index("name",inplace=True)
        previous_stats.set_index("name",inplace=True)

        changes = latest_stats - previous_stats
        return changes.round(decimals=2)

    def plot_stats_over_time(self, player):
        """
        Plots the players stats over time
        """
        data_player = self.data[(self.data['name'] == player)]
        data_player['date'] = pd.to_datetime(data_player['date'])
        data_player.sort_values(['date'], inplace=True)
        _, axes = plt.subplots(3, 2, figsize=(10, 12), sharex=True)
        variables = ['win_rate', 'hitting_efficiency', 'effectiveness', 'serving_percentage', 'serve_receive_rating', 'errors']
        limits = [[0, 100], [0, 1], [0, 10], [0.5, 1], [0, 3], [0, 7]]
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

            ax.plot((data_player['date'].unique()), variable_points, lw=3, color='black')
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            ax.xaxis.set_minor_locator(mdates.DayLocator(interval=7))
            ax.xaxis.set_minor_formatter(mdates.DateFormatter('%d'))
            ax.set_ylim(limit)
            ax.tick_params(axis='x', labelsize=12)
            ax.tick_params(axis='x', which="major",labelsize=14,pad=10)
            ax.tick_params(axis='y', labelsize=14)
            ax.set_title((variable.replace('_', ' ').title()), fontsize=18)
            
            for loc in ('top', 'right'):
                ax.spines[loc].set_visible(False)

        plt.savefig(f"{self.project_dir}/figures/{player}-stats_over_time.png")
        plt.close()

    def get_player_figure(self, player):
        """
        Gets the string corresponding to the player's statistics
        """
        return f"{self.project_dir}/figures/{player}-stats_over_time.png"

    def run(self, n_top_players=5):
        """
        Gets the statistics and generates the final report

        Parameters
        ----------
        n_top_players : int, default 5
            number of players to include on the leaderboard
        """
        self.logger.info("Calculating per game statistics")
        stats_per_game = self.calculate_per_game_stats(latest=True)

        self.logger.info("Getting leaderboard stats")
        results = {}
        top_results = {}
        bottom_results = {}
        mip_results = {}
        changes = self.compare_stats()
        for variable in stats_per_game.columns:
            if variable not in ('name', ):
                var_results = {}
                top_results = {}
                bottom_results = {}
                mip_results = {}
                if variable in ('errors', ):
                    ascend = True
                else:
                    ascend = False
                # top results
                top_results_per_variable = stats_per_game.sort_values(variable, ascending=ascend)[:n_top_players]
                for player, value in zip(top_results_per_variable['name'].values, top_results_per_variable[variable].values):
                    top_results[player] = value

                var_results["top"] = top_results
                
                # bottom results
                bot_results_per_variable = stats_per_game.sort_values(variable, ascending=not ascend)[:n_top_players]
                for player, value in zip(bot_results_per_variable['name'].values, bot_results_per_variable[variable].values):
                    bottom_results[player] = value
                
                var_results["bottom"] = bottom_results

                # mip results
                mip_results_per_variable = changes.sort_values(variable, ascending=ascend)[:n_top_players]
                for player, value in zip(mip_results_per_variable.index.values, mip_results_per_variable[variable].values):
                    mip_results[player] = value

                var_results["mip"] = mip_results

                results[variable] = var_results

        self.results = results

        for player in stats_per_game['name'].unique():
            self.plot_stats_over_time(player)

        templateLoader = jinja2.FileSystemLoader(searchpath=f'{self.project_dir}/templates/')
        templateEnv = jinja2.Environment(loader=templateLoader)
        func_dict = {'compare_stat':self.compare_stats, 
            'get_player_figure':self.get_player_figure}
        TEMPLATE_FILE = 'stat_update_template.html'
        template = templateEnv.get_template(TEMPLATE_FILE)
        template.globals.update(func_dict)
        outputText = template.render(date=self.date, previous_date=self.previous_date, n_games=self.total_games,
            win_rate=results['win_rate'],
            effectiveness=results['effectiveness'],
            point_diff=results["point_differential"],
            kills=results['kills'],
            efficiency=results['hitting_efficiency'],
            aces=results['aces'],
            serving=results['serving_percentage'],
            blocks=results['blocks'],
            errors=results['errors'],
            pass_rating=results['serve_receive_rating'],
            ace2error=results['ace2error'],
            top_teams=self.get_winningest_team(top_teams=n_top_players),
            per_player=self.get_simplified_results_per_player())
        html_file = open(f"{self.project_dir}/reports/hlb_report-{self.date}.html", 'w')
        html_file.write(outputText)
        html_file.close()
        pdfkit.from_file(f"{self.project_dir}/reports/hlb_report-{self.date}.html", f"{self.project_dir}/reports/hlb_report-{self.date}.pdf")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', help='date of report - should be string in format %m%d%Y', default='04272022',type=str)    
    parser.add_argument('-n', help='number players to use in leaderboard.', default=5, type=int) 
    args = parser.parse_args()

    # Generating the Report
    # ---------------------
    report = Report(args.d)
    report.run(args.n)