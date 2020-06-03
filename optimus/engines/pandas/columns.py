import re

import fastnumbers
import numpy as np
import pandas as pd
from sklearn.preprocessing import KBinsDiscretizer

from optimus.engines.base.dataframe.columns import DataFrameBaseColumns
from optimus.engines.jit import min_max, bincount
from optimus.engines.pandas.ml.encoding import index_to_string as ml_index_to_string
from optimus.engines.pandas.ml.encoding import string_to_index as ml_string_to_index
from optimus.helpers.check import equal_function
from optimus.helpers.columns import parse_columns, get_output_cols, check_column_numbers, prepare_columns
from optimus.helpers.constants import PROFILER_NUMERIC_DTYPES, PROFILER_STRING_DTYPES
from optimus.helpers.core import val_to_list, one_list_to_val
from optimus.helpers.parser import parse_dtypes
from optimus.infer import is_str, profiler_dtype_func, is_list

DataFrame = pd.DataFrame


def cols(self: DataFrame):
    class Cols(DataFrameBaseColumns):
        def __init__(self, df):
            super(DataFrameBaseColumns, self).__init__(df)

        @staticmethod
        def append(*args, **kwargs):
            pass

        @staticmethod
        def to_timestamp(input_cols, date_format=None, output_cols=None):
            pass

        @staticmethod
        def apply_expr(input_cols, func=None, args=None, filter_col_by_dtypes=None, output_cols=None, meta=None):
            pass

        @staticmethod
        def apply_by_dtypes(columns, func, func_return_type, args=None, func_type=None, data_type=None):
            pass

        def set(self, where=None, value=None, output_cols=None):

            df = self.df

            # output_cols = parse_columns(df, output_cols, accepts_missing_cols=True)

            # try to infer if we are going to handle the operations as numeric or string
            # Get first column in the operation
            def prepare_columns(cols):
                """
                Extract the columns names from the value and where clauses
                :param cols:
                :return:
                """
                r = None
                if is_str(cols):
                    r = val_to_list([f_col[1:len(f_col) - 1] for f_col in
                                     re.findall(r"\[(['A-Za-z0-9_']+)\]", cols.replace("\"", "'"))])
                    if len(r) == 0:
                        r = None
                return r


            columns = prepare_columns(value)
            if columns:
                first_columns = columns[0]
                where_columns = prepare_columns(where)
                if where_columns is not None:
                    columns = columns + where_columns
                # Remove duplicated columns
                columns = list(set(columns))

                column_dtype = df.cols.infer_profiler_dtypes(first_columns)[first_columns]
                # column_dtype = df.cols.profiler_dtypes(f_col)[f_col]

            else:

                if fastnumbers.fast_int(value):
                    column_dtype = "int"
                elif fastnumbers.fast_float(value):
                    column_dtype = "decimal"
                else:
                    column_dtype = "string"


            if column_dtype in PROFILER_NUMERIC_DTYPES:
                vfunc = lambda x: fastnumbers.fast_float(x, default=np.nan) if x is not None else None
            elif column_dtype in PROFILER_STRING_DTYPES or column_dtype is None:
                vfunc = lambda x: str(x) if not pd.isnull(x) else None
            else:
                raise

            def func(df, _value, _where, _output_col):

                try:
                    if where is None:
                        return eval(_value)
                    else:
                        df = pdf
                        _mask = (eval(_where))

                        mask = df[_mask]
                        df = mask
                        _value = eval(_value)  # <- mask is used here

                        df.loc[_mask, _output_col] = _value
                        return df[_output_col]
                        #
                        # mask = eval(_where)
                        # pdf = df
                        # print(_where)
                        # if fastnumbers.isreal(_value) or _value.isalnum():
                        #     r = pdf.mask(mask, _value)
                        #     print("AAA", r)
                        # else:
                        #     df = df[mask]  # This df is used inside the eval
                        #
                        #     r = pdf.mask(mask, eval(str(_value)))
                        #
                        # return r
                except:
                    raise
                    return np.nan

            # if df.cols.dtypes(input_col) == "category":
            #     try:
            #         # Handle error if the category already exist
            #         df[input_col] = df[input_col].cat.add_categories(val_to_list(value))
            #     except ValueError:
            #         pass
            output_cols = one_list_to_val(output_cols)


            if columns:
                pdf = df[columns].applymap(vfunc)
                final_value = func(pdf[columns], _value=value, _where=where, _output_col=output_cols)
            else:
                # df[output_cols] = value

                pdf = df.applymap(vfunc)
                final_value = func(pdf, _value=value, _where=where, _output_col=output_cols)
                # final_value = value

            kw_columns = {output_cols: final_value}
            return df.assign(**kw_columns)

        # @staticmethod
        # def cast(input_cols=None, dtype=None, output_cols=None, columns=None):
        #     df = self
        #     input_cols = parse_columns(df, input_cols)
        #     df[input_cols] = df[input_cols].astype(dtype)
        #
        #     return df

        @staticmethod
        def astype(*args, **kwargs):
            pass

        @staticmethod
        def move(column, position, ref_col=None):
            pass

        def mode(self, columns):
            df = self.df
            columns = parse_columns(df, columns)
            result = {}
            for col_name in columns:
                result[col_name] = df[col_name].mode(col_name)[0]
            return result

        @staticmethod
        def create_exprs(columns, funcs, *args):
            df = self
            # Std, kurtosis, mean, skewness and other agg functions can not process date columns.
            filters = {"object": [df.functions.min, df.functions.stddev],
                       }

            def _filter(_col_name, _func):
                for data_type, func_filter in filters.items():
                    for f in func_filter:
                        if equal_function(func, f) and \
                                df.cols.dtypes(_col_name)[_col_name] == data_type:
                            return True
                return False

            columns = parse_columns(df, columns)
            funcs = val_to_list(funcs)

            result = {}

            for func in funcs:
                # Create expression for functions that accepts multiple columns
                filtered_column = []
                for col_name in columns:
                    # If the key exist update it
                    if not _filter(col_name, func):
                        filtered_column.append(col_name)
                if len(filtered_column) > 0:
                    result = func(columns, args, df=df)

            return result

        @staticmethod
        def replace(input_cols, search=None, replace_by=None, search_by="chars", ignore_case=False, output_cols=None):
            df = self
            input_cols = parse_columns(df, input_cols)
            output_cols = get_output_cols(input_cols, output_cols)
            # If tupple

            search = val_to_list(search)

            if search_by == "chars":
                str_regex = "|".join(map(re.escape, search))
            elif search_by == "words":
                str_regex = (r'\b%s\b' % r'\b|\b'.join(map(re.escape, search)))
            else:
                str_regex = search
            if ignore_case is True:
                _regex = re.compile(str_regex, re.IGNORECASE)
            else:
                _regex = re.compile(str_regex)

            # df = df.cols.cast(input_cols, "str")
            for input_col, output_col in zip(input_cols, output_cols):
                if search_by == "chars" or search_by == "words":
                    df[output_col] = df[input_col].str.replace(_regex, replace_by)
                elif search_by == "full":
                    df[output_col] = df[input_col].replace(search, replace_by)

            return df

        @staticmethod
        def exec_agg(exprs):
            return exprs

        @staticmethod
        def remove(columns, search=None, search_by="chars", output_cols=None):
            pass

        @staticmethod
        def remove_accents(input_cols, output_cols=None):
            df = self
            input_cols = parse_columns(df, input_cols)
            output_cols = get_output_cols(input_cols, output_cols)
            # cols = df.select_dtypes(include=[np.object]).columns

            for input_col, output_col in zip(input_cols, output_cols):
                if df[input_col].dtype == "object":
                    df[output_col] = df[input_col].str.normalize('NFKD').str.encode('ascii',
                                                                                    errors='ignore').str.decode('utf-8')
            return df

        @staticmethod
        def date_transform(input_cols, current_format=None, output_format=None, output_cols=None):
            pass

        @staticmethod
        def years_between(input_cols, date_format=None, output_cols=None):
            pass

        def year(self, input_cols, output_cols=None):
            pass

        def month(self, input_cols, output_cols=None):
            pass

        def day(self, input_cols, output_cols=None):
            pass

        def hour(self, input_cols, output_cols=None):
            pass

        def minute(self, input_cols, output_cols=None):
            pass

        def second(self, input_cols, output_cols=None):
            pass

        def weekday(self, input_cols, output_cols=None):
            pass

        def weekofyear(self, input_cols, output_cols=None):
            pass

        @staticmethod
        def extract(input_cols, output_cols, regex):
            df = self
            from optimus.engines.base.dataframe.commons import extract
            df = extract(df, input_cols, output_cols, regex)
            return df

        @staticmethod
        def min_max(columns):
            """
            Calculate min max in one pass.
            :param columns:
            :return:
            """

            df = self
            columns = parse_columns(df, columns)
            result = {}
            for col_name in columns:
                _min, _max = min_max(df[col_name].to_numpy())
                result[col_name] = {"min": _min, "max": _max}
            return result

        @staticmethod
        def count_na(columns):
            df = self
            columns = parse_columns(df, columns)
            result = {}

            def _count_na(_df, _serie):
                return np.count_nonzero(_df[_serie].isnull().values.ravel())

            for col_name in columns:
                # np is 2x faster than df[columns].isnull().sum().to_dict()
                # Reference https://stackoverflow.com/questions/28663856/how-to-count-the-occurrence-of-certain-item-in-an-ndarray-in-python
                result[col_name] = _count_na(df, col_name)
            return result

        @staticmethod
        def count_zeros(columns):
            pass

        @staticmethod
        def unique(columns):
            pass

        @staticmethod
        def nunique_approx(columns):
            df = self
            return df.cols.nunique(columns)

        # NLP
        @staticmethod
        def stem_words(input_col):
            df = self

        @staticmethod
        def lemmatize_verbs(input_cols, output_cols=None):
            df = self

            def func(value, args=None):
                return value + "aaa"

            df = df.cols.apply(input_cols, func, output_cols)
            return df

        def remove_stopwords(self):
            df = self

        def remove_numbers(self):
            df = self
            self.text = re.sub('[-+]?[0-9]+', '', self.text)
            return self

        def strip_html(self):
            df = self
            # soup = BeautifulSoup(self.text, "html.parser")
            # self.text = soup.get_text()
            return self

        # @staticmethod
        # def mismatches_1(columns, dtype):
        #     """
        #     Find the rows that have null values
        #     :param dtype:
        #     :param columns:
        #     :return:
        #     """
        #     df = self
        #     columns = parse_columns(df, columns)
        #
        #     from optimus.infer import is_bool, is_list
        #
        #     def func(d_type):
        #         if d_type == "bool":
        #             return is_bool
        #         elif d_type == "int":
        #             return fastnumbers.isint
        #         elif d_type == "float":
        #             return fastnumbers.isfloat
        #         elif d_type == "list":
        #             return is_list
        #         elif d_type == "str":
        #             return None
        #         elif d_type == "object":
        #             return None
        #
        #     f = func(dtype)
        #     if f is None:
        #         for col_name in columns:
        #             # df[col_name + "__match_positions__"] = df[col_name].apply(get_match_positions, args=sub)
        #             df = df[df[col_name].apply(f)]
        #         return df

        @staticmethod
        def is_match(columns, dtype, invert=False):
            """
            Find the rows that match a data type
            :param columns:
            :param dtype: data type to match
            :param invert: Invert the match
            :return:
            """
            df = self
            columns = parse_columns(df, columns)

            dtype = parse_dtypes(df, dtype)
            f = profiler_dtype_func(dtype)
            if f is not None:
                for col_name in columns:
                    df = df[col_name].apply(f)
                    df = ~df if invert is True else df
                return df

        @staticmethod
        def find(columns, sub, ignore_case=False):
            """
            Find the start and end position for a char or substring
            :param columns:
            :param ignore_case:
            :param sub:
            :return:
            """
            df = self
            columns = parse_columns(df, columns)
            sub = val_to_list(sub)

            def get_match_positions(_value, _separator):

                result = None
                if is_str(_value):
                    # Using re.IGNORECASE in finditer not seems to work
                    if ignore_case is True:
                        _separator = _separator + [s.lower() for s in _separator]
                    regex = re.compile('|'.join(_separator))

                    length = [[match.start(), match.end()] for match in
                              regex.finditer(_value)]
                    result = length if len(length) > 0 else None
                return result

            for col_name in columns:
                # Categorical columns can not handle a list inside a list as return for example [[1,2],[6,7]].
                # That could happened if we try to split a categorical column
                # df[col_name] = df[col_name].astype("object")
                df[col_name + "__match_positions__"] = df[col_name].astype("object").apply(get_match_positions,
                                                                                           args=(sub,))
            return df

        @staticmethod
        def cell(column):
            pass

        @staticmethod
        def scatter(columns, buckets=10):
            pass

        @staticmethod
        def frequency_by_group(columns, n=10, percentage=False, total_rows=None):
            pass

        @staticmethod
        def count_mismatch(columns_mismatch: dict = None):
            pass

        @staticmethod
        def count_by_dtypes(columns, dtype):
            print("dtype", dtype)
            df = self
            result = {}
            df_len = len(df)
            for col_name, na_count in df.cols.count_na(columns).items():
                # for i, j in df.constants.DTYPES_DICT.items():
                #     if j == df[col_name].dtype.type:
                #         _dtype = df.constants.SHORT_DTYPES[i]

                # _dtype = df.cols.dtypes(col_name)[col_name]

                mismatches_count = df.cols.is_match(col_name, dtype).value_counts().to_dict().get(False)
                mismatches_count = 0 if mismatches_count is None else mismatches_count
                result[col_name] = {"match": df_len - na_count, "missing": na_count,
                                    "mismatch": mismatches_count - na_count}
            print(result)
            return result

        @staticmethod
        def correlation(input_cols, method="pearson", output="json"):
            pass

        @staticmethod
        def boxplot(columns):
            pass

        @staticmethod
        def qcut(columns, num_buckets, handle_invalid="skip"):
            pass

        @staticmethod
        def clip(columns, lower_bound, upper_bound):
            pass

        @staticmethod
        def values_to_cols(input_cols):
            pass

        @staticmethod
        def string_to_index(input_cols=None, output_cols=None, columns=None):
            df = self
            df = ml_string_to_index(df, input_cols, output_cols, columns)

            return df

        @staticmethod
        def index_to_string(input_cols=None, output_cols=None, columns=None):
            df = self
            df = ml_index_to_string(df, input_cols, output_cols, columns)

            return df

        @staticmethod
        def bucketizer(input_cols, splits, output_cols=None):
            df = self

            columns = prepare_columns(df, input_cols, output_cols, merge=True)

            for input_col, output_col in columns:
                x = df[[input_col]]
                est = KBinsDiscretizer(n_bins=splits, encode='ordinal', strategy='uniform')
                est.fit(input_col)
                df[output_col] = est.transform(x)
            return df

        @staticmethod
        def abs(input_cols, output_cols=None):
            """
            Apply abs to the values in a column
            :param input_cols:
            :param output_cols:
            :return:
            """
            df = self
            input_cols = parse_columns(df, input_cols, filter_by_column_dtypes=df.constants.NUMERIC_TYPES)
            output_cols = get_output_cols(input_cols, output_cols)

            check_column_numbers(output_cols, "*")
            # Abs not accepts column's string names. Convert to Spark Column

            # TODO: make this in one pass.

            for input_col, output_col in zip(input_cols, output_cols):
                df[output_col] = df.compute(np.abs(df[input_col]))
            return df

        @staticmethod
        def nunique(columns):
            df = self
            columns = parse_columns(df, columns)
            result = {}
            # def _nunique(_df, _serie_name):
            #     return np.unique(_df[_serie_name].values.ravel())

            for col_name in columns:
                result[col_name] = df[col_name].nunique()

                # result[col_name] = _nunique(df,col_name)
            return result

        # def count(self):
        #     df = self.df
        #     return len(df.columns)

        @staticmethod
        def h_freq(columns):
            df = self
            columns = parse_columns(df, columns)
            result = {}
            for col_name in columns:
                df["hash"] = df[col_name].apply(hash)
                m = df["hash"].value_counts().nlargest().to_dict()

                # print(m)
                for l, n in m.items():
                    print(df[df["hash"] == l].iloc[0][col_name], n)
                return

        @staticmethod
        def frequency(columns, n=10, percentage=False, total_rows=None):
            # https://stackoverflow.com/questions/10741346/numpy-most-efficient-frequency-counts-for-unique-values-in-an-array
            df = self
            columns = parse_columns(df, columns)

            result = {}
            for col_name in columns:
                col_values = []
                if df[col_name].dtype == np.int64 or df[col_name].dtype == np.float64:
                    i, j = bincount(df[col_name], n)

                    # result[col_name] = {"values": list(i), "count": list(j)}
                else:
                    # Value counts
                    r = df[col_name].value_counts().nlargest(n)
                    i = r.index.tolist()
                    j = r.tolist()
                col_values = [{"value": _i, "count": _j} for _i, _j in zip(i, j)]

                result[col_name] = {"frequency": col_values}
            return result

    return Cols(self)


DataFrame.cols = property(cols)
