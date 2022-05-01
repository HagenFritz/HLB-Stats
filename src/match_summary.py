import pandas as pd
import pathlib
import argparse

from datetime import datetime

class MatchSummary:

    def __init__(self,id) -> None:
        """
        Parameters
        ----------
        id : str
            ID for the match

        Creates
        -------
        id : str
            copied from input; ID for the match
        data : DataFrame
            stats
        """
        self.id = id

        # file paths
        self.path_to_this_dir = f"{pathlib.Path(__file__).resolve().parent}"
        self.project_dir = f"{pathlib.Path(__file__).resolve().parent.parent}" # taking advantage of project filesystem

        # game stats
        self.data = self.import_sheet_data("stats")

        # play data
        self.plays = {}
        for sheet in ["hammers","monster_blocks","superb_serves","great_defense","wow_plays"]:
            self.plays[sheet] = self.import_sheet_data(sheet)

    def import_sheet_data(self,sheet_name="stats",datetime_columns=["date"]):
        """
        Imports data from the given sheet
        """
        df = pd.read_excel(f'{self.project_dir}/data/pickup_stats.xlsx',sheet_name=sheet_name)
        for col in datetime_columns:
            df[col] = pd.to_datetime(df[col])
        # removing any columns that don't have data - "match_id" should always be included
        df.dropna(subset=['match_id'], inplace=True)
        return df

    def generate_video_description(self, match_id=None, one_liner=None,
    variables=['kills','serving_percentage','aces','hitting_efficiency','blocking_efficiency','errors']):
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
        if match_id is None:
            match_id = self.id

        match_data = self.data[(self.data['match_id'] == f"{match_id}")]
        players = []
        for player in match_data['name']:
            players.append(player)
        
        # output of players
        print(f"{players[0].title()}/{players[1].title()} vs {players[2].title()}/{players[3].title()}\n\n")
        
        # one liner
        if one_liner:
            print(one_liner)
            print()

        # winning team and score
        team1_points = match_data.iloc[0]['points_for']
        team2_points = match_data.iloc[0]['points_against']
        winner1 = match_data[(match_data['win_loss'] == 'win')].iloc[0]['name']
        winner2 = match_data[(match_data['win_loss'] == 'win')].iloc[1]['name']
        print(f"{int(team1_points)} - {int(team2_points)} Game {winner1}/{winner2}\n")

        # switches
        # switches are given with the winning team's score first in the data so the order
        # might need to be reversed if the winning team is the second team listed
        print("Switches:")
        for i in range(8):
            switch_str = match_data.iloc[0][f"switch{i+1}"]
            if str(switch_str).lower() != "nan":
                if winner1 == match_data.iloc[0]["name"]: # switches are in order already
                    print(switch_str)
                else:
                    score_winner = switch_str.split(" - ")[0]
                    score_loser = switch_str.split(" - ")[1]
                    print(f"{score_loser} - {score_winner}")
        print()

        # plays
        for play_name, play_data in self.plays.items():
            play_data_match = play_data[play_data["match_id"] == match_id]
            if len(play_data_match) > 0:
                print(f'{play_name.replace("_"," ").title()}:')
                for player, ts in zip(play_data_match["name"],play_data_match["timestamp"]):
                    print(f"{player.title()} {ts}")

                print()
        
        # player-specific stats summary
        for player in match_data['name']:
            player_data = match_data[(match_data['name'] == player)]
            effectiveness = int(player_data['effectiveness'].values[0])
            if effectiveness > 0:
                sign_annot = '+'
            else:
                sign_annot = ''
            print(f"{player.title()} ({sign_annot}{effectiveness})")
            # looping through remaining variables
            for variable in variables:
                value = player_data[variable].values[0]
                if variable == "hitting_efficiency":
                    swings = int(player_data["swings"].values[0])
                    print(f"\tSwings: {swings} ({round(value * 100, 1)}%)")
                elif variable == "serving_percentage":
                    serves = int(player_data["serves"].values[0])
                    print(f"\tServes: {serves} ({round(value * 100, 1)}%)")
                elif variable == "blocking_efficiency":
                    blocks = int(player_data["blocks"].values[0])
                    print(f"\tBlocks: {blocks} ({round(value * 100, 1)}%)") 
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        value = 0
                
                    print(f"\t{variable.replace('_', ' ').title()}: {value}")
                    
            print()
            
        print("Match ID:", match_id)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', help='ID of the match, typically in the form of mmddyyyy_n where "n" refers the game number for that day', default='02082022_1',type=str)    
    args = parser.parse_args()

    # Generating the Report
    # ---------------------
    summary = MatchSummary(args.i)
    summary.generate_video_description()