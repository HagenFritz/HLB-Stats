import pandas as pd

class Base:

    def __init__(self) -> None:
        self.data = pd.read_excel('pickup_stats.xlsx', parse_dates=['date'])
        self.data.dropna(subset=['date'], inplace=True)


class Explore(Base):

    def generate_video_description(self, match_id, one_liner=None, variables=[
 'kills', 'blocks', 'aces', 'hitting_efficiency', 'serving_percentage', 'errors']):
        """
        Generates the descriptive stats for the video description
        
        Parameters
        ----------
        match_id : str
            unique game identifier
        one_liner : str, default None
            quipy one-liner to include at the top. If None, nothing is included
            
        Prints
        ------
        <description> : str
            text to place in the video description
        """
        match_data = self.data[(self.data['match_id'] == match_id)]
        players = []
        for player in match_data['name']:
            players.append(player)
        else:
            print(f"{players[0].title()}/{players[1].title()} vs {players[2].title()}/{players[3].title()}\n\n")
            if one_liner:
                print(one_liner)
                print()
            team1_points = match_data.iloc[0]['points_for']
            team2_points = match_data.iloc[0]['points_against']
            winner1 = match_data[(match_data['win_loss'] == 'win')].iloc[0]['name']
            winner2 = match_data[(match_data['win_loss'] == 'win')].iloc[1]['name']
            print(f"{int(team1_points)} - {int(team2_points)} Game {winner1}/{winner2}\n")
            for player in match_data['name']:
                player_data = match_data[(match_data['name'] == player)]
                effectiveness = int(player_data['effectiveness'].values[0])
                if effectiveness > 0:
                    sign_annot = '+'
                else:
                    sign_annot = ''
                print(f"{player.title()} ({sign_annot}{effectiveness})")
                for variable in variables:
                    value = player_data[variable].values[0]
                    if value < 1:
                        value = round(value * 100, 1)
                        percent_annot = '%'
                    else:
                        try:
                            value = int(value)
                        except ValueError:
                            value = 0
                        else:
                            percent_annot = ''
                        print(f"\t{variable.replace('_', ' ').title()}: {value}{percent_annot}")
                else:
                    print()


class Report(Base):

    def __init__(self) -> None:
        pass