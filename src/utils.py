import pandas as pd
import re
import os
from pathlib import Path
from typing import List, Optional

def get_regions_mapping(
        regions: pd.Series,
        regions_key: pd.DataFrame,
) -> pd.Series:
    """Map region identifiers to Zillow region names using a provided key.

    Args:
        regions (pd.Series): A pandas Series containing region identifiers to be mapped.
        regions_key (pd.DataFrame): A DataFrame that contains the mapping for all possible 'key_row' to 'zillow_region_name'.

    Returns:
        pd.Series: A pandas Series with region identifiers replaced by their corresponding Zillow region names that is used as an identifier in other data sources.
    """
    key_row_mapper = regions_key[['key_row', 'zillow_region_name']]
    key_row_mapper.drop_duplicates(['key_row'], keep='first', inplace=True)
    key_row_mapper = key_row_mapper.set_index('key_row')
    key_row_mapper = key_row_mapper.to_dict()['zillow_region_name']
    mapped_regions = regions.map(key_row_mapper)
    return mapped_regions

def get_census_stats(
        census_data: pd.DataFrame,
        index_name: str,
        metric_suffix: str,
) -> pd.Series:
    """Extract and clean a specific label metric for all regions of MHI or population census statistics files.

    Args:
        census_data (pd.DataFrame): A DataFrame containing census statistics (either MHI or population).
        index_name (str): The name of the index label to filter.
        metric_suffix (str): The added suffix to region names that is used to identify the relevant metric columns.

    Returns:
        pd.Series: A Series of the filtered and cleaned census label metric for all regions.
    """
    total_stats = census_data[census_data.iloc[:, 0] == "    " + index_name].iloc[0]
    metric_mask = total_stats.index.str.endswith(metric_suffix)
    filtered_stats = total_stats[metric_mask]
    filtered_stats.index = filtered_stats.index.str.replace(re.escape(metric_suffix), "", regex=True)
    return filtered_stats

def add_census_stat_with_blurb(
    output_df: pd.DataFrame,
    census_data_df: pd.DataFrame,
    index_name: str,
    metric_suffix: str,
    stat_column_name: str,
    rank_and_blurb_prefix: str,
    blurb_template: str,
    override_data_df: Optional[pd.DataFrame]=None,
) -> pd.DataFrame:
    """Add census statistic, its rankings, and a generated blurb to the output DataFrame.

    Args:
        output_df (pd.DataFrame): The base DataFrame to which the census statistic, rank, and blurb will be added.
        census_data_df (pd.DataFrame): A census statistics DataFrame (either MHI or population) used as the source of the metric.
        index_name (str): The name of the label index to extract from the census data.
        metric_suffix (str): The suffix used to filter the desired metric columns in the census data.
        stat_column_name (str): The name to assign to the extracted and formatted statistic column in the output DataFrame.
        rank_and_blurb_prefix (str): A prefix used for naming the rank and blurb columns.
        blurb_template (str): A string template used to generate the blurb, expecting placeholders like `{region}` and `{rank}`.
        override_data_df (Optional[pd.DataFrame], optional): An optional DataFrame containing override values for the statistic. Defaults to None.

    Returns:
        pd.DataFrame: The updated DataFrame with the added census statistic, rank, and generated blurb columns.
    """
    output_df = output_df.copy()

    # Get and rename the census stat
    full_stat_series = get_census_stats(
        census_data=census_data_df,
        index_name=index_name,
        metric_suffix=metric_suffix
    )
    full_stat_series.rename(stat_column_name, inplace=True)
    
    # Join to output_df and format numbers
    output_df = output_df.join(full_stat_series, how='left', on='mapped_key_row')
    output_df[stat_column_name] = format_numbers(output_df[stat_column_name])
    
    # Apply overrides if available
    if override_data_df is not None and stat_column_name in override_data_df.columns:
        override_values = override_data_df[stat_column_name].combine_first(
            output_df.set_index('key_row')[stat_column_name]
        )
        output_df[stat_column_name] = override_values.reindex(output_df['key_row']).values

    # Rank and generate blurb
    rank_col_name = f"{rank_and_blurb_prefix}_rank"
    blurb_col_name = f"{rank_and_blurb_prefix}_blurb"
    output_df[rank_col_name] = get_rank(output_df[stat_column_name])
    output_df[blurb_col_name] = generate_blurb(
        df=output_df,
        blurb_template=blurb_template,
        region="mapped_key_row",
        rank=rank_col_name,
    )
    
    return output_df

def get_median_sale_price(
        data: pd.DataFrame,
) -> pd.Series:
    """Clean latest date data of median sale price file to only numeric representation.

    Args:
        data (pd.DataFrame): A pandas DataFrame containing sale price data, with rows representing different regions and columns representing sorted dates.

    Returns:
        pd.Series: A cleaned pandas Series containing of most recent date sale price data for each region.
    """
    last_date_data = data.iloc[:, -1]
    last_date_data = last_date_data \
                            .str.replace("K", "000") \
                            .str.replace(r"$", "")
    return last_date_data

def ordinal(n: int) -> str:
    """Convert an integer into its ordinal representation (e.g., 1 -> '1st', 2 -> '2nd'), and in case of 0 (non valid rank) return empty string.

    Args:
        n (int): The integer to convert to an ordinal string.

    Returns:
        str: The ordinal representation of the input integer.
    """
    if n == 0:
        return ""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def format_numbers(
        numbers_series: pd.Series,
) -> pd.Series:
    """Clean and convert a series of numeric strings to proper numeric values.

    Args:
        numbers_series (pd.Series): A pandas Series containing numeric values or strings with numeric formatting (e.g., '$1,000').

    Returns:
        pd.Series: A numeric pandas Series with formatting characters removed and values converted to numbers.
    """
    if not pd.api.types.is_numeric_dtype(numbers_series):
        return pd.to_numeric(numbers_series.str.replace(r'[^0-9.]', '', regex=True))   # clean symbols like `$`, `,` and convert to numeric 
    return numbers_series

def get_rank(
        numbers_series: pd.Series,
        ascending: bool=False,
) -> pd.Series:
    """Rank the values in a series and return their ordinal representation (e.g., '1st', '2nd').

    Args:
        numbers_series (pd.Series): A pandas Series containing numeric values to be ranked.
        ascending (bool, optional): Whether to rank in ascending order. Defaults to False.

    Returns:
        pd.Series: A pandas Series containing the ordinal rankings of the input values.
    """
    rankings = numbers_series.rank(ascending=ascending, method='min').fillna(0).astype(int)
    rankings_with_suffix = rankings.apply(ordinal)
    return rankings_with_suffix

def generate_blurb(
        df: pd.DataFrame,
        blurb_template: str,
        **columns
):
    """Generate a blurb for each row in a DataFrame using any number of columns mapped to template placeholders, ignore place holder and return empty if any of the placeholder values is empty.

    Args:
        df (pd.DataFrame): A pandas DataFrame containing the data to use for generating the blurbs.
        blurb_template (str): A string template for the blurb, where placeholders are replaced by column values (e.g. "{city} is {rank}").
        **columns: mapping of template placeholders to DataFrame column names.

    Returns:
        pd.Series: A pandas Series containing the generated blurbs for each row.
    """
    def format_blurb(row):
        values = {k: row[v] for k, v in columns.items()}    # collect unpacked blurb template placeholders to dictionary
        if all(value != "" for value in values.values()):
            return blurb_template.format(**values)
        return ""
    return df.apply(format_blurb, axis=1)

def load_override_data(path: Path):
    """Load additional data with a CSV format that overrides the original data sources.

    Args:
        path (Path): The file path to the override data.

    Raises:
        ValueError: If the file format is not CSV.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the loaded override data.
    """
    if path.suffix.lower() == '.csv':
        return pd.read_csv(path, index_col=0)
    else:
        raise ValueError("Unsupported override data format.")

def save_formatted_xlsx(
        df: pd.DataFrame,
        number_cols: List[str],
        currency_cols: List[str],
        output_dir: str,
        file_name: str,
) -> None:
    """Save a DataFrame to a formatted Excel file with number and currency column formatting.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        number_cols (List[str]): List of column names to format as numbers (with comma separators).
        currency_cols (List[str]): List of column names to format as currency (with dollar sign and comma separators).
        output_dir (str): Directory where the Excel file will be saved.
        file_name (str): Name of the output Excel file.

    Returns:
        None: The function saves the formatted Excel file to disk and does not return a value.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, file_name)
    try:
        with pd.ExcelWriter(output_path) as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')

            # Access workbook and worksheet
            workbook  = writer.book
            worksheet = writer.sheets['Sheet1']

            # Formats
            bold_format = workbook.add_format({'bold': True})   # Bold Header
            number_format = workbook.add_format({'num_format': '#,##0'})    # Integer format
            currency_format = workbook.add_format({'num_format': '$#,##0'})  # Currency format
            
            for col_num, column_title in enumerate(df.columns.values):
                worksheet.write(0, col_num, column_title, bold_format)
                
                # Apply number and currency format
                col_letter = chr(65 + col_num)  # 'A' is 65 in ASCII
                if column_title in number_cols:
                    worksheet.set_column(f'{col_letter}:{col_letter}', None, number_format)
                elif column_title in currency_cols:
                    worksheet.set_column(f'{col_letter}:{col_letter}', None, currency_format)
            print(f"✅ File saved to {output_path}")
    except Exception as e:
        print(f"❌ An error occurred while writing the Excel file: {e}")