# data-analysis-on-nz-news-trend

### Abstract/Summary  
This project aims to answer the research question : “Are the news of NZ in January similar in terms of their event nature compared to those from February to April in 2020?” The “event nature” in the research question is an event actor-event category pair, and the relationship of each pair will be analysed for interest value to answer the research question.  
  
### Python Libraries Used  
* Pyspark - Python API to support Apache Spark
* Os - Provides a way of using operating system dependent functionality
* Gdelt - Python-based framework to retrieve GDELT Event Database for analysis
* Pandas - Python package providing fast, flexible and expressive data structures to make working with Gdelt data easy and intuitive

### Tools Used  
* Google Cloud - Executed the data analysis code on google cloud by adjusting number of processors on worker nodes and recorded the effect of scalability on data

### Concepts Integrated  
* Market-basket analysis
* A-priori algorithm
* Cosine similarity

### Result
Degree of event similarities compared between the month of January and February-April 2020  
{'202001': 1.0, '202002': 0.06045845748511886, '202003': 0.0005235420902709003, '202004': 0.026152294802553322}

### Conclusion  
No, the events in every other month do not have similar event nature compared to events in January 2020. 






