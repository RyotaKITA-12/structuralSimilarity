#!/usr/bin/env python
# coding: utf-8

# In[4]:


import numpy as np
import pandas as pd

df=pd.read_csv('./data.csv', encoding='shift_jis', header=2)
df


# ## 欠損値がある行を削除する

# In[5]:


df.dropna(how='any', inplace=True)
df


# ## 天気番号の対応表を用意(これは定義なので固定)

# In[6]:


tenkinb=pd.Series(np.arange(1,25))
tenki=pd.Series(['快晴', '晴れ', '薄曇', '曇', '煙霧', '砂じん嵐', '地ふぶき', '霧', '霧雨', '雨', 'みぞれ', '雪', 'あられ', 'ひょう', '雷', 'しゅう雨または止み間のある雨', '着氷性の雨', '着氷性の霧雨', 'しゅう雪または止み間のある雪', '霧雪', '凍雨', '細氷', 'もや', '降水またはしゅう雨性の降水'])
df_tenki = pd.DataFrame({'天気' : tenkinb, '天候' : tenki})
df_tenki


# ## 天気番号の対応表を結合することで天候の列を元のdataframeに追加する

# In[7]:


df_sum=pd.merge(df, df_tenki, on='天気')
df_sum


# ## 時間ごとの天候の割合("時"と"天候"のクロス集計)

# In[8]:


pd.crosstab(df_sum['時'],df_sum['天候'], normalize='index', margins=True)


# In[9]:


import matplotlib.pyplot as plt
get_ipython().run_line_magic('matplotlib', 'inline')
import japanize_matplotlib

# 時間と天候でクロス集計、列で正規化
tmp=pd.crosstab(df_sum['時'],df_sum['天候'], normalize='index', margins=True)

tmp.plot(kind='bar')
plt.show()


# In[16]:


tmp=pd.crosstab(df_sum['時'],df_sum['天候'], normalize='index', margins=True)


# In[11]:


tmp2=pd.crosstab(df_sum['時'], df_sum['天候'], values=df['気温(℃)'], aggfunc='mean')
tmp2


# In[12]:


tmp2.mean(axis='columns')


# In[13]:


plt.plot(tmp2.mean(axis='columns'))
plt.show()


# In[15]:


tmp2.mean(axis='index')


# In[17]:


width = 0.4

g1=plt.bar(np.array(tmp.index[0:7]),tmp['晴れ'][0:7]+tmp['快晴'][0:7], color='orange', width = width, label='晴れ・快晴')
g2=plt.bar(np.array(tmp.index[0:7])+width,tmp['曇'][0:7]+tmp['薄曇'][0:7], color='gray', width = width, label='曇り・薄曇')
g3=plt.bar(np.array(tmp.index[0:7])+width*2,tmp['雨'][0:7], color='blue', width = width, label='雨')
plt.legend(handles=[g1,g2,g3],loc='best',shadow=True)
plt.show()

