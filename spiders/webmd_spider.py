from webmd.items import WebmdItem
from scrapy import Spider, Request
from scrapy.selector import Selector
import urllib
import re
import html

headers = {'User-Agent': 'Chrome/60.0.3112.113', 
           'enc_data': 'OXYIMo2UzzqFUzYszFv4lWP6aDP0r+h4AOC2fYVQIl8=', 
           'timestamp': 'Mon, 04 Sept 2017 04:35:00 GMT', 
           'client_id': '3454df96-c7a5-47bb-a74e-890fb3c30a0d'}
            
class WebmdSpider(Spider):
    
    name = "webmd"
    allowed_urls = ['http://www.webmd.com/']
    start_urls = ['http://www.webmd.com/drugs/2/index']
    drug_dict = {}

    def parse(self, response):
        atoz = response.xpath('//ul[@class="browse-letters squares"]')[0].xpath("li/a/@href").extract()
        for i in range(len(atoz)):
            yield Request(response.urljoin(atoz[i]), 
                          callback = self.parse_sub, 
                          dont_filter = True)
        print("keys: " + str(WebmdSpider.drug_dict.keys()))
        yield Request(response.urljoin('/drugs/2/conditions/index'),
                      callback = self.parse_conditions,
                      dont_filter = True)
            
    def parse_sub(self, response):
        sub = response.xpath('//ul[@class="browse-subletters squares"]')[0].xpath("li/a/@href").extract()
        for i in range(len(sub)):
            yield Request(response.urljoin(sub[i]), 
                          callback = self.parse_drug, 
                          dont_filter = True)
    
    def parse_drug(self, response):
        drug_list = response.xpath('//ul[@class="drug-list"]')[0].xpath("li/a")
        for i in range(len(drug_list)):
            yield Request(response.urljoin(drug_list[i].xpath("@href")[0].extract()),
                          callback = self.parse_details, 
                          meta = {'Drug': drug_list[i].xpath("text()")[0].extract().lower()},
                          dont_filter = True)    

    def parse_details(self, response):
        Use = ' '.join(response.xpath(
                                     '//*[@id="ContentPane28"]/div/div/div/div[3]/div[1]/div[1]/h3/preceding-sibling::p//text()'
                                     ).extract())
        HowtoUse = ' '.join(response.xpath(
                                          '//*[@id="ContentPane28"]/div/div/div/div[3]/div[1]/div[1]/h3/following-sibling::p//text()'
                                          ).extract())
        Sides = ' '.join(response.xpath(
                                        '//*[@id="ContentPane28"]/div/div/div/div[3]/div[2]/div/p//text()'
                                       ).extract()).replace('\r\n', '')
        Precautions = ' '.join(response.xpath('//*[@id="ContentPane28"]/div/div/div/div[3]/div[3]/div/p//text()').extract())
        Interactions = ' '.join(response.xpath('//*[@id="ContentPane28"]/div/div/div/div[3]/div[4]/div[1]/p//text()').extract())
        tRevurl = response.xpath('//*[@id="ContentPane28"]/div/div/div/div[2]/nav/ul/li[7]/a//@href')
        if len(tRevurl) is not 0:
            revurl = tRevurl.extract()[0]    
            if not Use:
                Use = ' '
            if not Sides:
                Sides = ' '
            if not Interactions:
                Interactions = ' '
            if not Precautions:
                Precautions = ' '
            if not HowtoUse:
                HowtoUse = ' '
            if re.search('COMMON BRAND NAME', response.body.decode('utf-8')):
                Brand = response.xpath('//*[@id="ContentPane28"]/div/header/section/section[1]/p/text()')
                if (len(Brand) is 0) or (not Brand[0].extract()):
                    BrandName = ' '
                else:
                    BrandName = Brand[0].extract()
                Gen = response.xpath('//*[@id="ContentPane28"]/div/header/section/section[2]/p/text()')
                if (len(Gen) is 0) or (not Gen[0].extract()):
                    GenName = ' '
                else:
                    GenName = Gen[0].extract()
            elif re.search('GENERIC NAME', response.body.decode('utf-8')):
                BrandName = ' '
                Gen = response.xpath('//*[@id="ContentPane28"]/div/header/section/section[1]/p/text()')
                if (len(Gen) is 0) or (not Gen[0].extract()):
                    GenName = ' '
                else:
                    GenName = Gen[0].extract()
            else:
                GenName = ' '
                BrandName = ' '
            yield Request(response.urljoin(response.url + '/list-contraindications'),
                          callback = self.parse_avoid,
                          meta = {'Drug': response.meta['Drug'], 
                                  'Use': Use,
                                  'HowtoUse': HowtoUse,
                                  'Sides': Sides,
                                  'Precautions': Precautions,
                                  'Interactions': Interactions,
                                  'revurl': revurl,
                                  'BrandName': BrandName,
                                  'GenName': GenName},
                          dont_filter = True)

    def parse_avoid(self, response):
        if re.search("We\'re sorry, but we couldn\'t find the page you tried", response.body.decode('utf-8')):
            AvoidUse = ' '
            Allergies = ' '
        elif re.search('Conditions:', response.body.decode('utf-8')):
            AvoidUse = ' '.join(response.xpath('//*[@id="ContentPane28"]/div/article/section/p[2]/text()').extract())
            Allergies = ' '.join(response.xpath('//*[@id="ContentPane28"]/div/article/section/p[3]/text()').extract())
        elif re.search('Allergies:', response.body.decode('utf-8')):
            AvoidUse = ' '
            Allergies = ' '.join(response.xpath('//*[@id="ContentPane28"]/div/article/section/p[2]/text()').extract())
        else:
            AvoidUse = ' '
            Allergies = ' '
        if not AvoidUse:
            AvoidUse = ' '
        if not Allergies:
            Allergies = ' '
        yield Request(response.urljoin(response.meta['revurl']),
                      callback = self.parse_reviews,
                      meta = {'Drug': response.meta['Drug'], 
                              'Use': response.meta['Use'],
                              'HowtoUse': response.meta['HowtoUse'],
                              'Sides': response.meta['Sides'],
                              'Precautions': response.meta['Precautions'],
                              'Interactions': response.meta['Interactions'],
                              'BrandName': response.meta['BrandName'],
                              'GenName': response.meta['GenName'],
                              'AvoidUse': AvoidUse,
                              'Allergies': Allergies},
                      dont_filter = True)

    def parse_reviews(self, response):
        if re.search('Rate this treatment and share your opinion', response.body.decode('utf-8')) \
           or re.search('Be the first to share your experience with this treatment', response.body.decode('utf-8')):
            WebmdSpider.drug_dict[response.meta['Drug']] = {'Use': response.meta['Use'],
                                                            'HowtoUse': response.meta['HowtoUse'],
                                                            'Sides': response.meta['Sides'],
                                                            'Precautions': response.meta['Precautions'],
                                                            'Interactions': response.meta['Interactions'],
                                                            'BrandName': response.meta['BrandName'],
                                                            'GenName': response.meta['GenName'],
                                                            'AvoidUse': response.meta['AvoidUse'],
                                                            'Allergies': response.meta['Allergies'],
                                                            'Effectiveness': ' ',
                                                            'EaseOfUse': ' ',
                                                            'Satisfaction': ' ',
                                                            'Reviews': [{}]}
        else:
            NumReviews = int(response.xpath('//span[@class="totalreviews"]/text()')[0].extract().replace(" Total User Reviews", ""))  
            url = 'http://www.webmd.com/drugs/service/UserRatingService.asmx/GetUserReviewSummary?repositoryId=1&primaryId='
            DrugId = re.search('(drugid=)(\d+)', response.url).group(2)
            url2 = '&secondaryId=-1&secondaryIdValue='
            id2 = urllib.parse.quote(re.sub("\s+", " ", response.xpath('//option[@value = -1]//text()').extract()[0]).strip())
            yield Request(url + DrugId + url2 + id2,
                          callback = self.parse_ratings,
                          meta = {'Drug': response.meta['Drug'], 
                                  'Use': response.meta['Use'],
                                  'HowtoUse': response.meta['HowtoUse'],
                                  'Sides': response.meta['Sides'],
                                  'Precautions': response.meta['Precautions'],
                                  'Interactions': response.meta['Interactions'],
                                  'BrandName': response.meta['BrandName'],
                                  'GenName': response.meta['GenName'],
                                  'AvoidUse': response.meta['AvoidUse'],
                                  'Allergies': response.meta['Allergies'],
                                  'DrugId': DrugId,
                                  'NumReviews': NumReviews},
                          dont_filter = True)
                
    def parse_ratings(self, response):
        if re.search('("xsd:string">)(\d+.\d+)', response.xpath('//*/*').extract()[3]):
            Effectiveness = re.search('("xsd:string">)(\d+.\d+)', response.xpath('//*/*').extract()[3]).group(2)
        else:
            Effectiveness = re.search('("xsd:string">)(\d+)', response.xpath('//*/*').extract()[3]).group(2)
        if re.search('("xsd:string">)(\d+.\d+)', response.xpath('//*/*').extract()[4]):
            EaseofUse = re.search('("xsd:string">)(\d+.\d+)', response.xpath('//*/*').extract()[4]).group(2)
        else:
            EaseofUse = re.search('("xsd:string">)(\d+)', response.xpath('//*/*').extract()[4]).group(2)
        if re.search('("xsd:string">)(\d+.\d+)', response.xpath('//*/*').extract()[5]):
            Satisfaction = re.search('("xsd:string">)(\d+.\d+)', response.xpath('//*/*').extract()[5]).group(2)
        else:
            Satisfaction = re.search('("xsd:string">)(\d+)', response.xpath('//*/*').extract()[5]).group(2)
        url = "http://www.webmd.com/drugs/service/UserRatingService.asmx/GetUserReviewsPagedXml?repositoryId=1&objectId="
        url2 = "&pageIndex=0&pageSize="
        url3 = "&sortBy=DatePosted"
        yield Request(url + response.meta['DrugId'] + url2 + str(response.meta['NumReviews']) + url3,
                      method = 'GET', headers=headers,
                      callback = self.parse_all_reviews,
                      meta = {'Drug': response.meta['Drug'], 
                              'Use': response.meta['Use'],
                              'HowtoUse': response.meta['HowtoUse'],
                              'Sides': response.meta['Sides'],
                              'Precautions': response.meta['Precautions'],
                              'Interactions': response.meta['Interactions'],
                              'BrandName': response.meta['BrandName'],
                              'GenName': response.meta['GenName'],
                              'AvoidUse': response.meta['AvoidUse'],
                              'Allergies': response.meta['Allergies'],
                              'DrugId': response.meta['DrugId'],
                              'NumReviews': response.meta['NumReviews'],
                              'Effectiveness': Effectiveness,
                              'EaseofUse': EaseofUse,
                              'Satisfaction': Satisfaction},
                      dont_filter = True)
        
    def parse_all_reviews(self, response):
        n = response.meta['NumReviews']
        data = Selector(text=html.unescape(response.xpath("//*")[0].extract()).replace("<![CDATA[", "").replace("]]>", ""))
        Reviews = [{} for i in range(int(n))]
        for i in range(int(n)):
            t_Id = data.xpath("//userreviewid")[i].xpath("text()")
            Reviews[i]['Id'] = ' ' if len(t_Id) is 0 else t_Id[0].extract()
            t_Condition = data.xpath("//secondaryvalue")[i].xpath("text()")
            Reviews[i]['Condition'] = ' ' if len(t_Condition) is 0 else t_Condition[0].extract()
            t_IsPatient = data.xpath("//boolean2")[i].xpath("text()")
            Reviews[i]['IsPatient'] = ' ' if len(t_IsPatient) is 0 else t_IsPatient[0].extract()
            t_IsMale = data.xpath("//boolean1")[i].xpath("text()")
            Reviews[i]['IsMale'] = ' ' if len(t_IsMale) is 0 else t_IsMale[0].extract()
            t_Age = data.xpath("//lookuptext1")[i].xpath("text()")
            Reviews[i]['Age'] = ' ' if len(t_Age) is 0 else t_Age[0].extract()
            t_TimeUsingDrug = data.xpath("//lookuptext2")[i].xpath("text()")
            Reviews[i]['TimeUsingDrug'] = ' ' if len(t_TimeUsingDrug) is 0 else t_TimeUsingDrug[0].extract()
            t_DatePosted = data.xpath("//dateposted")[i].xpath("text()")
            Reviews[i]['DatePosted'] = ' ' if len(t_DatePosted) is 0 else t_DatePosted[0].extract()
            t_Comment = data.xpath("//userexperience")[i].xpath("text()")
            Reviews[i]['Comment'] = ' ' if len(t_Comment) is 0 else t_Comment[0].extract()
            t_Effectiveness = data.xpath("//ratingcriteria1")[i].xpath("text()")
            Reviews[i]['Effectiveness'] = ' ' if len(t_Effectiveness) is 0 else t_Effectiveness[0].extract()
            t_EaseOfUse = data.xpath("//ratingcriteria2")[i].xpath("text()")
            Reviews[i]['EaseOfUse'] = ' ' if len(t_EaseOfUse) is 0 else t_EaseOfUse[0].extract()
            t_Satisfaction = data.xpath("//ratingcriteria3")[i].xpath("text()")
            Reviews[i]['Satisfaction'] = ' ' if len(t_Satisfaction) is 0 else t_Satisfaction[0].extract()
            t_NumFoundHelpful = data.xpath("//foundhelpfulcount")[i].xpath("text()")
            Reviews[i]['NumFoundHelpful'] = ' ' if len(t_NumFoundHelpful) is 0 else t_NumFoundHelpful[0].extract()
            t_NumVoted = data.xpath("//totalvotedcount")[i].xpath("text()")
            Reviews[i]['NumVoted'] = ' ' if len(t_NumVoted) is 0 else t_NumVoted[0].extract()
        WebmdSpider.drug_dict[response.meta['Drug']] = {'Use': response.meta['Use'],
                                                        'HowtoUse': response.meta['HowtoUse'],
                                                        'Sides': response.meta['Sides'],
                                                        'Precautions': response.meta['Precautions'],
                                                        'Interactions': response.meta['Interactions'],
                                                        'BrandName': response.meta['BrandName'],
                                                        'GenName': response.meta['GenName'],
                                                        'AvoidUse': response.meta['AvoidUse'],
                                                        'Allergies': response.meta['Allergies'],
                                                        'DrugId': response.meta['DrugId'],
                                                        'NumReviews': response.meta['NumReviews'],
                                                        'Effectiveness': response.meta['Effectiveness'],
                                                        'EaseofUse': response.meta['EaseofUse'],
                                                        'Satisfaction': response.meta['Satisfaction'],
                                                        'Reviews': Reviews} 
            
    def parse_conditions(self, response):
        atoz = response.xpath('//ul[@class="browse-letters squares"]')[0].xpath("li/a/@href").extract()
        for i in range(len(atoz)):
            yield Request(response.urljoin(atoz[i]),
                          callback = self.parse_condition,
                          dont_filter = True)
            
    def parse_condition(self, response):
        drug_list = response.xpath('//ul[@class="drug-list"]')[0].xpath("li/a")
        for i in range(len(drug_list)):
            yield Request(response.urljoin(drug_list[i].xpath("@href")[0].extract()),
                          callback = self.parse_condition_drug, 
                          meta = {'Condition' : drug_list[i].xpath("text()")[0].extract()}, 
                          dont_filter = True)
    
    def parse_condition_drug(self, response):
        drugs = response.xpath("//table[@class='drugs-treatments-table']")[0].xpath("tbody/tr") 
        for i in range(len(drugs)):
            Drug = drugs[i].xpath("td")[0].xpath("a/text()")[0].extract().lower()
            Indication = drugs[i].xpath("td")[1].xpath("text()")[0].extract()
            Type = drugs[i].xpath("td")[2].xpath("text()")[0].extract().replace('\r\n', '')
            if Drug not in WebmdSpider.drug_dict:
                print("ANOMALY: " + Drug)
            else:    
                info = WebmdSpider.drug_dict[Drug]
                item = WebmdItem()
                item['Condition'] = response.meta['Condition']
                item['Drug'] = Drug
                item['Indication'] = Indication
                item['Type'] = Type
                for key in info.keys():
                    item[key] = info[key]
                yield item