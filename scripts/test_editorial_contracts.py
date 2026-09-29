import sys, pathlib
p=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(p))
from src.editorial_engine import EditorialEngine
from src.validator import CarouselValidator
from src.workflow_agents import PromptEngineer, GrammarAgent
from src.news_comprehension_agent import NewsComprehensionAgent
ed=EditorialEngine(api_key=''); ed.client=None
slides=[{'role':'hook','title':'Will this change your EMI?'}]+[{'role':f'value_{i}','title':f'Check the actual term {i}','card_text':'Read the lender notice first'} for i in range(1,7)]+[{'role':'bookmark_save','title':'Check your loan terms','cta_detail':'Check the lender notice before changing your repayment plan. Save this check.'}]
topic={'title':'Bank changes loan terms','raw_text':'Bank changes loan terms.'}
normalized=ed._normalize_slides(slides,topic); assert CarouselValidator.validate_content({'slides':normalized})[0]; assert 'loan' in ' '.join(normalized[-1]['title_lines']).lower(); assert normalized[-1]['cta_detail']==slides[-1]['cta_detail']
try:
 ed._normalize_slides(slides[:-1]+[{'role':'bookmark_save','title':'Save'}],topic)
 raise AssertionError('Missing final takeaway accepted')
except ValueError: pass
assert PromptEngineer().build_brief({'hook_headline':'Loan terms'})
assert NewsComprehensionAgent(api_key='')._build_deterministic_analysis({'title':'Loan term change','numbers_detected':[]})['citable_metrics']==[]
print('editorial contracts OK:',p.name)
