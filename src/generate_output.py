from pathlib import Path
import argparse
from utils import *

def main():
    parser = argparse.ArgumentParser(description="Data pipeline settings")
    parser.add_argument(
        '--override-data',
        type=str,
        # default='inpu_data/override_data.csv'
        help='Path to a CSV file with override data'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='input_data',
        help='Directory of input CSV files'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Directory of generated output file'
    )
    parser.add_argument(
        '--output-fname',
        type=str,
        default='OUTPUT.xlsx',
        help='Output excel file name'
    )
    args = parser.parse_args()

    # Reading data sources
    data_path = Path(args.data_dir)
    census_population_df = pd.read_csv(data_path / 'CENSUS_POPULATION_STATE.tsv', sep='\t')
    census_mhi_df = pd.read_csv(data_path / 'CENSUS_MHI_STATE.csv')
    regions_key_df = pd.read_csv(data_path / 'KEYS.csv')
    redfin_median_sale_price_df = pd.read_csv(data_path / 'REDFIN_MEDIAN_SALE_PRICE.csv', index_col=0, skiprows=1)

    if args.override_data:
        print(f"Loading override data from {args.override_data}")
        override_data_df = load_override_data(args.override_data)
    else:
        override_data_df = pd.DataFrame()

    output_df = pd.read_csv(data_path / 'key_row.csv')
    output_df['mapped_key_row'] = get_regions_mapping(regions=output_df['key_row'], regions_key=regions_key_df)

    # 1. Get census_population, population_rank, and population_blurb
    output_df = add_census_stat_with_blurb(
        output_df=output_df,
        census_data_df=census_population_df,
        index_name="Total population",
        metric_suffix="!!Estimate",
        stat_column_name="census_population",
        rank_and_blurb_prefix='population',
        blurb_template="{region} is {rank} in the nation in population among states, DC, and Puerto Rico.",
        override_data_df=override_data_df,
    )

    # 2. Get median_household_income, median_household_income_rank, and median_household_income_blurb
    output_df = add_census_stat_with_blurb(
        output_df=output_df,
        census_data_df=census_mhi_df,
        index_name="Households",
        metric_suffix="!!Median income (dollars)!!Estimate",
        stat_column_name="median_household_income",
        rank_and_blurb_prefix='median_household_income',
        blurb_template="{region} is {rank} in the nation in median household income among states, DC, and Puerto Rico.",
        override_data_df=override_data_df,
    )

    # 3. Get median_sale_price, median_sale_price_rank, and median_sale_price_blurb
    full_median_sale_price = get_median_sale_price(redfin_median_sale_price_df)
    full_median_sale_price.rename('median_sale_price', inplace=True)
    output_df = output_df.join(full_median_sale_price, how='left', on='mapped_key_row')
    output_df['median_sale_price'] = format_numbers(output_df['median_sale_price'])
    if 'median_sale_price' in override_data_df.columns:
        override_values = override_data_df['median_sale_price'].combine_first(output_df.set_index('key_row')['median_sale_price'])
        output_df['median_sale_price'] = override_values.reindex(output_df['key_row']).values
    output_df['median_sale_price_rank'] = get_rank(output_df['median_sale_price'])
    last_median_sale_price_date = pd.to_datetime(redfin_median_sale_price_df.columns[-1]).strftime("%B %Y")
    output_df['median_sale_price_blurb'] = generate_blurb(
        df=output_df,
        blurb_template="{region} has the {rank} highest median sale price on homes in the nation among states, DC, and Puerto Rico, according to Redfin data from " + f"{last_median_sale_price_date}.",
        region="mapped_key_row", rank='median_sale_price_rank'
    )

    # 4. Get house_affordability_ratio, house_affordability_ratio_rank, and house_affordability_ratio_blurb
    output_df['house_affordability_ratio'] = (output_df['median_sale_price'] / output_df['median_household_income']).round(1)
    output_df['house_affordability_ratio_rank'] = get_rank(output_df['house_affordability_ratio'], ascending=True)
    output_df['house_affordability_ratio_blurb'] = generate_blurb(
        df=output_df,
        blurb_template="{region} has the {rank} lowest house affordability ratio in the nation among states, DC, and Puerto Rico, according to Redfin data from " + f"{last_median_sale_price_date}.",
        region="mapped_key_row", rank='median_sale_price_rank'
    )

    # Drop extra columns, format currency & number columns, and save excel file
    currency_cols = ['median_household_income', 'median_sale_price']
    number_cols = ['census_population']
    output_df.drop(columns="mapped_key_row", inplace=True)
    save_formatted_xlsx(
        df=output_df,
        number_cols=number_cols,
        currency_cols=currency_cols,
        output_dir=args.output_dir,
        file_name=args.output_fname
    )

if __name__ == "__main__":
    main()