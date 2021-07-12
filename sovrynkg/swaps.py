# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/swaps.ipynb (unless otherwise specified).

__all__ = ['get_swap_df', 'lookup_token_name']

# Cell
import pandas as pd
import numpy as np
from .knowledge_graph import Query
from .contracts import whatis

def get_swap_df(skip=None, limit=None):
    q = Query()
    q.add("MATCH (b:Block)-[]->(:Transaction)-[]->()-[calls:CALLS]->(amm:Contract) ")
    q.add("WHERE amm.address='0x98ace08d2b759a265ae326f010496bcd63c15afc'")
    q.add("RETURN b.signed_at as signed_at,")
    q.add("""
    calls._toAmount as to_amount,
    calls._fromAmount as from_amount,
    calls._toToken as to_token,
    calls._fromToken as from_token,
    calls._smartToken as smart_token,
    calls._trader as trader
    """)
    if skip:
        q.add("SKIP {}".format(skip))
    if limit:
        q.add("LIMIT {}".format(limit))

    swaps = q.data()
    df = pd.DataFrame(swaps)
    df['signed_at'] = pd.to_datetime(df['signed_at'])


    df['to_token'] = df.apply(lambda row: lookup_token_name(row, 'to_token'), axis='columns')
    df['from_token'] = df.apply(lambda row: lookup_token_name(row, 'from_token'), axis='columns')
    df['trader'] = df.apply(lambda row: lookup_token_name(row, 'trader'), axis='columns')

    df['to_amount'] = df.to_amount.astype(np.double)
    df['from_amount'] = df.from_amount.astype(np.double)
    return df

def lookup_token_name(row, col_name):
    address = row[col_name]
    matching_tokens = whatis(address)
    if matching_tokens:
        return matching_tokens[0].name
    else:
        return address