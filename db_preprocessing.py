import os
import pandas as pd 
from tqdm import tqdm
import datetime


us_state_to_abbrev = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC"
}

abbrev_to_us_state = dict(map(reversed, us_state_to_abbrev.items()))

def load_FBI_hate_crimes_DB():
    hate_crimes = pd.read_csv(os.path.join('Data', 'hate_crime.csv'), parse_dates=['incident_date'])

    remove_cols = ['victim_count', 'total_individual_victims', 'juvenile_victim_count', 'adult_victim_count',
                'total_offender_count', 'adult_offender_count', 'juvenile_offender_count',
                'data_year', 'incident_id', 'victim_types', 'multiple_offense', 'multiple_bias', 'division_name',
                'region_name', 'offender_race', 'offender_ethnicity', 'location_name']
    hate_crimes = hate_crimes.drop(columns=remove_cols)


    # Some hate crimes are federal, swap to make the data consistent according to actual city
    hate_crimes.loc[hate_crimes["state_abbr"] == "FS", 'pug_agency_name'] = hate_crimes.loc[
        hate_crimes["state_abbr"] == "FS", 'pub_agency_unit']
    hate_crimes.loc[hate_crimes["state_abbr"] == "FS", 'pub_agency_unit'] = 'FBI'
    hate_crimes.loc[hate_crimes["state_abbr"] == "FS", 'state_abbr'] = hate_crimes.loc[
        hate_crimes["state_abbr"] == "FS", 'ori'].apply(lambda x: x[:2])
    # The FBI for some reason chose a non-official abbreviation for nebraska
    hate_crimes.loc[hate_crimes.state_abbr == 'NB', "state_abbr"] = 'NE'
    hate_crimes = hate_crimes.drop(hate_crimes[hate_crimes['state_abbr'] == 'PR'].index)
    hate_crimes.loc[hate_crimes["state_name"] == "Federal", 'state_name'] = hate_crimes.loc[
        hate_crimes["state_name"] == "Federal", 'state_abbr'].apply(
        lambda x: abbrev_to_us_state[x])
    # For crimes that are committed in District of Columbia, but there's no FBI unit named, this refers to Washington D.C
    hate_crimes.loc[(hate_crimes["state_abbr"] == 'DC') &
                    (~pd.notna(hate_crimes['pug_agency_name'])),"pug_agency_name"] = 'Washington'





    ethno_biases = ['Anti-Arab', 'Anti-Asian', 'Anti-Other Race/Ethnicity/Ancestry',
                    'Anti-Black or African American', 'Anti-Hispanic or Latino',
                    'Anti-American Indian or Alaska Native', 'Anti-Native Hawaiian or Other Pacific Islander']
    relig_biases = ['Anti-Buddhist', 'Anti-Hindu', 'Anti-Other Religion',
                    'Anti-Sikh', 'Anti-Islamic (Muslim)', 'Anti-Jewish']
    needed_biases = ['Gay', 'Lesbian', 'Bisexual', 'Transgender', 'Gender Non-Conforming']
    hate_crimes_biases = hate_crimes[~hate_crimes['bias_desc'].str.contains('|'.join(needed_biases))]
    hate_crimes_ethno = hate_crimes_biases[hate_crimes_biases['bias_desc'].str.contains('|'.join(ethno_biases))]
    hate_crimes_relig = hate_crimes_biases[hate_crimes_biases['bias_desc'].str.contains('|'.join(relig_biases))]
    hate_crimes = hate_crimes[hate_crimes['bias_desc'].str.contains('|'.join(needed_biases))]

    return hate_crimes, hate_crimes_relig, hate_crimes_ethno


def load_votes_DB():
    def make_party_rows_into_column_features(db):
        for party in db["party_simplified"].unique():
            db.loc[db["party_simplified"] == party, f'{party}_candidatevotes'] = db.loc[
                db["party_simplified"] == party, 'candidatevotes']
            if party == 'Democrat':
                db.loc[db["party_simplified"] == party, f'{party}_totalvotes'] = db.loc[
                    db["party_simplified"] == party, 'totalvotes']
            db.loc[db["party_simplified"] == party, f'{party}_votes_percent'] = db.loc[
                db["party_simplified"] == party, 'votes_percent']
        db = db.groupby(by=['year', 'state']).mean().reset_index().drop(
            columns=['candidatevotes', 'totalvotes', 'votes_percent']).rename(columns={'state': 'State', 'Democrat_totalvotes': 'totalvotes'})
        return db.fillna(0)
    

    votes_house = pd.read_csv(os.path.join('Data', 'Votes', '1976-2020-house.csv'))
    votes_senate = pd.read_csv(os.path.join('Data', 'Votes', '1976-2020-senate.csv'), encoding='unicode_escape')
    votes_presid = pd.read_csv(os.path.join('Data', 'Votes', '1976-2020-president.csv'))

    votes_house = votes_house.drop(votes_house[votes_house.stage != 'GEN'].index)
    votes_house = votes_house.drop(
        columns=['state_fips', 'state_cen', 'state_ic',
                'office', 'candidate','writein',
                'unofficial', 'version', 'stage', 'special', 'mode', 'fusion_ticket'])
    votes_house_district = votes_house.groupby(by=['year', 'state', 'district', 'party']).sum().reset_index()
    votes_house_state = votes_house.groupby(by=['year', 'state', 'party']).sum().reset_index().drop(columns=['district'])
    votes_house_district["votes_percent"] = votes_house_district["candidatevotes"] / votes_house_district["totalvotes"] 
    votes_house_state["votes_percent"] = votes_house_state["candidatevotes"] / votes_house_state["totalvotes"] 

    votes_senate = votes_senate.drop(votes_senate[votes_senate.stage != 'gen'].index)
    votes_senate = votes_senate.drop(
        columns=['state_fips', 'state_cen', 'state_ic',
                'candidate', 'office', 'party_detailed',
                'writein', 'unofficial', 'version', 'stage', 'mode', 'district'])
    votes_senate = votes_senate.groupby(by=['year', 'state', 'party_simplified']).sum().reset_index()
    votes_senate["votes_percent"] = votes_senate["candidatevotes"] / votes_senate["totalvotes"] 

    votes_presid = votes_presid.drop(
        columns=['state_fips', 'state_cen', 'state_ic',
                'candidate', 'version', 'notes',
                'writein', 'party_detailed', 'office'])
    votes_presid = votes_presid.groupby(by=['year', 'state', 'party_simplified']).sum().reset_index()
    votes_presid["votes_percent"] = votes_presid["candidatevotes"] / votes_presid["totalvotes"] 

    # Captialize state names (NEW YORK -> New York)
    votes_presid["state"] = votes_presid["state"].apply(str.title)
    votes_senate["state"] = votes_senate["state"].apply(str.title)
    votes_presid.loc[votes_presid["state"] == 'District Of Columbia',"state"] = 'District of Columbia'
    votes_senate.loc[votes_senate["state"] == 'District Of Columbia',"state"] = 'District of Columbia'

    # Captialize party names
    votes_presid["party_simplified"] = votes_presid["party_simplified"].apply(str.title)
    votes_senate["party_simplified"] = votes_senate["party_simplified"].apply(str.title)

    votes_presid = make_party_rows_into_column_features(votes_presid)
    votes_senate = make_party_rows_into_column_features(votes_senate)

    return votes_presid, votes_senate


def aggregate_hc_data(db, path, timedelta):
    # If the aggregated data doesn't exist in the folder, create it
    if not os.path.exists(path):
        time_delta = datetime.timedelta(timedelta)
        dates_range = pd.date_range(db['incident_date'].min() + time_delta, 
                                    db['incident_date'].max())

        ret = db.groupby(['pug_agency_name', 'state_abbr'], as_index=False).agg({'incident_date': list})
        ret = ret.reindex(
            columns=['pug_agency_name', 'state_abbr', 'incident_date'] + dates_range.to_list(),
            fill_value=0)

        for _, (index, row) in tqdm(enumerate(ret.iterrows()), total=len(ret)):
            tmp_dates_range = dates_range.to_frame().reset_index().drop(columns=[0])
            tmp_dates_range['count'] = 0
            for date in row['incident_date']:
                tmp_dates_range.loc[(date <= tmp_dates_range['index']) & (tmp_dates_range['index'] <= time_delta + date),
                                    'count'] += 1
            tmp_dates_range = tmp_dates_range.set_index('index').transpose()
            ret.iloc[index, 3:] = tmp_dates_range.values.ravel()

        ret.to_csv(path)
    else:  # Load aggregated data
        ret = pd.read_csv(path)
        ret = ret.iloc[:, 1:]
    return ret


def expand_state_yearly(db, year_col_name, state_col_name, mindate, maxdate, inner_level=None, def_month=1):
    """Take a DB that has yearly information, and duplicated the rows such that the returned DB has daily information
    
    inner_level - deprecated"""
    new_df = []
    drop_cols = [year_col_name, state_col_name] + ([inner_level] if inner_level is not None else [])
    old_columns = db.columns.drop(drop_cols)  # Feature columns
    
    for state in db[state_col_name].unique():
        inner_cond = [None]  # depracated, everyone will have [None]
        if inner_level is not None:
            inner_cond = db[inner_level].unique()
        
        state_df = []
        for inner in inner_cond:  # depracated, always happens once
            # Create exapnded sub-frame
            tmp_df = pd.date_range(mindate, maxdate).to_frame().reset_index().drop(
                columns=['index']).rename(columns={0: 'Date'}).reindex(columns=old_columns.insert(0, 'Date'))
            
            # Calc conditions
            is_cur_state = db[state_col_name] == state
            is_inner = (db[inner_level] == inner) if inner is not None else True
            
            
            if not len(db.loc[is_cur_state & is_inner, year_col_name].unique()):  # depracated
                # No such inner category value for this state in this year
                continue
            
            # First Years
            prev_year = sorted(db.loc[is_cur_state & is_inner, year_col_name].unique())[0]

            prev_date = pd.to_datetime(datetime.date(year=prev_year, month=def_month, day=1))
            # For all the dates we need to fill that happened before the first year of the current DB data, 
            # fill with the first year data (extrapolate)
            tmp_df.loc[tmp_df['Date'] <= prev_date, old_columns] = db.loc[
                is_cur_state & is_inner & (db[year_col_name] == prev_year),
                old_columns].reset_index().iloc[0, 1:].values

            # Middle Years
            for year in sorted(db.loc[is_cur_state & is_inner, year_col_name].unique())[1:]:
                tmp_date = pd.to_datetime(datetime.date(year=year, month=def_month, day=1))
                # For all the dates we need to fill the happened in a given year, 
                # fill the given year's data (Interpolate with 0-hold filter)
                tmp_df.loc[(prev_date < tmp_df['Date']) & (tmp_df['Date'] <= tmp_date), old_columns
                            ] = db.loc[is_cur_state & is_inner & (db[year_col_name] == year),
                                       old_columns].reset_index().iloc[0, 1:].values
                prev_date = tmp_date

            # Last Years
            # For all the dates we need to fill that happened after the last year of the current DB data,
            # fill with the last year's data (extrapolate)
            tmp_df.loc[prev_date < tmp_df['Date'], old_columns] = db.loc[
                is_cur_state & is_inner & (db[year_col_name] == year), old_columns].reset_index().iloc[0, 1:].values

            if inner_level is not None:
                tmp_df[inner_level] = inner
            state_df.append(tmp_df)

        state_df = pd.concat(state_df)
        state_df[state_col_name] = state
        new_df.append(state_df)
    return pd.concat(new_df).reset_index().drop(columns=['index'])
    