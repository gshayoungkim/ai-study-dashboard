from flask import Flask, render_template, jsonify, request
from github import Github, GithubException
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import re
import time
from supabase import create_client, Client

# 로컬 개발 환경 지원
if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__)

# GitHub 토큰 설정
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or os.getenv('GITHUB_TOKEN_BACKUP')

print("\n" + "=" * 60)
print("[DEBUG] 환경변수 확인")
print(f"GITHUB_TOKEN 존재 여부: {GITHUB_TOKEN is not None}")
if GITHUB_TOKEN:
    print(f"토큰 앞부분: {GITHUB_TOKEN[:20]}...")
    print(f"토큰 길이: {len(GITHUB_TOKEN)}")
else:
    print("⚠️ GITHUB_TOKEN이 None입니다!")
    print(f"현재 작업 디렉토리: {os.getcwd()}")
    print(f".env 파일 존재: {os.path.exists('.env')}")
    
    # .env 파일 내용 확인 (토큰은 가림)
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            lines = f.readlines()
            print(".env 파일 내용:")
            for line in lines:
                if 'GITHUB_TOKEN' in line:
                    print(f"  찾음: GITHUB_TOKEN=***")
                else:
                    print(f"  {line.strip()}")
print("=" * 60 + "\n")

# GitHub 연결
if GITHUB_TOKEN:
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        print(f"✓ GitHub 연결 성공: {user.login}\n")
    except Exception as e:
        print(f"✗ GitHub 연결 실패: {str(e)}\n")
        g = None
else:
    g = None
    print("✗ GitHub 토큰이 없어서 연결할 수 없습니다\n")

# Supabase 설정
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"\n{'='*60}")
    print("[INIT] Supabase 연결 확인")
    print(f"  URL: {SUPABASE_URL[:30]}...")
    print(f"{'='*60}\n")
else:
    supabase = None
    print("[WARNING] Supabase 환경 변수 없음")

QUIZ_DATA_FILE = 'quiz_results.json'

cache = {
    'submissions': None,
    'last_updated': 0,
    'cache_duration': 300
}

# QUIZZES 데이터
QUIZZES = {
    "ch01": [
        {
            "id": "ch01",
            "title": "Ch01-1 - 머신러닝 개요",
            "gemini_link": "https://gemini.google.com/share/cd026cf98350"
        },
    ],
    "ch02": [
        {
            "id": "ch02-1",
            "title": "Ch02-1 - 훈련 세트와 테스트 세트 퀴즈",
            "gemini_link": "https://gemini.google.com/share/f1f3d7a544e3"
        },
        {
            "id": "ch02-2",
            "title": "Ch02-2 - 데이터 전처리",
            "gemini_link": "https://gemini.google.com/share/d13ebaf4c393"
        }
    ],
    "ch03": [
        {
            "id": "ch03",
            "title": "Ch03 - 회귀알고리즘과 모델 규제",
            "gemini_link": "https://gemini.google.com/share/f9fa458276d3"
        }
    ],
    "ch04": [
        {
            "id": "ch04-1",
            "title": "Ch04 - 다양한 알고리즘(1)",
            "gemini_link": "https://gemini.google.com/share/4ea0e7137b74"
        },
        {
            "id": "ch04-2",
            "title": "Ch04 - 다양한 알고리즘(2)",
            "gemini_link": "https://gemini.google.com/share/770a512a89ef"
        }
    ],
    "ch05": [
        {
            "id": "ch05-1",
            "title": "Ch05-1 - 결정트리",
            "gemini_link": "https://gemini.google.com/share/58b3bbcd177d"
        },
        {
            "id": "ch05-2",
            "title": "Ch05-2 - 교차검증과 그리드서치",
            "gemini_link": "https://gemini.google.com/share/5fe85dc6304d"
        },
        {
            "id": "ch05-3",
            "title": "Ch05-3 - 트리의 앙상블",
            "gemini_link": "https://gemini.google.com/share/5e9c9c72468f"
        }
    ],
    "ch06": [
        {
            "id": "ch06-1",
            "title": "Ch06-1 - 군집 알고리즘",
            "gemini_link": "https://gemini.google.com/share/6e89a727743c"
        },
        {
            "id": "ch06-2",
            "title": "Ch06-2 - k-평균",
            "gemini_link": "https://gemini.google.com/share/0345af73e04c"
        },
        {
            "id": "ch06-3",
            "title": "Ch06-3 - 주성분 분석 퀴즈",
            "gemini_link": "https://gemini.google.com/share/be17f7e135ad"
        }
    ],
        "ch07": [
        {
            "id": "ch07-1",
            "title": "Ch07-1 - 인공 신경망",
            "gemini_link": "https://gemini.google.com/share/b8528ac6dbf0"
        },
        {
            "id": "ch07-2",
            "title": "Ch07-2 - 심층 신경망",
            "gemini_link": "https://gemini.google.com/share/640cc2d73541"
        },
        {
            "id": "ch07-3",
            "title": "Ch07-3 - 신경망 모델 훈련",
            "gemini_link": "https://gemini.google.com/share/73bdf741009e"
        }
    ],
       "ch08": [
        {
            "id": "ch08-1",
            "title": "Ch08-1 - 합성곱 신경망의 구성 요소",
            "gemini_link": "https://gemini.google.com/share/2d06aac1361e"
        },
        {
            "id": "ch08-2",
            "title": "Ch08-2 - 합성곱 신경망을 사용한 이미지 분류",
            "gemini_link": "https://gemini.google.com/share/e90cd14ae9f6"
        },
        {
            "id": "ch08-3",
            "title": "Ch08-3 - 합성곱 신경망의 시각화",
            "gemini_link": "https://gemini.google.com/share/4d37b2e8bab0"
        }
    ]
}

# 레포지토리 매핑
REPO_NAME_MAPPING = {
    "hayoung-kim": "김하영",
    "minjeong-ko": "고민정",
    "hagyeong-lee": "이하경",
    "yeonseok-kim": "김연석",
    "eunyong-choi": "최은용",
    "sujeung-kim": "김수정",
    "yunjae-gim": "김윤재",
    "seongyeong-kim": "김선경",
    "soyeon-park": "박소연",
    "zeho-oh": "오제호",
    "yeji-kim": "김예지",
    "jihoon-jung": "정지훈",
    "sieun-lee": "이시은",
    "suhyeon-min": "민수현",
    "sungkyeong-bae": "배성경",
    "jiwoo-yoon": "윤지우",
    "bonwook-gu": "구본욱",
    "sungmin-hwang": "황성민",
    "soyeon-lee": "이소연",
    "sooneun-bae": "배순은",
    "dayeon-kang": "강다연",
    "hyein-lee": "이혜인",
    "jooyoung-lee": "이주영",
    "youlim-hong": "홍유림",
    "heejoon-kang": "강희준",
    "chanho-ma": "마찬호",
    "juyoung-noh": "노주영",
    "sulim-lee": "이수림",
    "yoonjung-koo": "구윤정",
    "hyoeun-ji" : "지효은",
    "seonmin-lee" : "이선민",
    "heeseung-han" : "한희승",
    "yejin-moon" : "문예진",
    "subin-han" : "한수빈",
    "subin-shin" : "신수빈",
    "seungmin-lee" : "이승민",


}

PART1_MEMBERS = [
    "hayoung-kim",
    "minjeong-ko", 
    "hagyeong-lee",
    "yeonseok-kim",
    "eunyong-choi",
    "sujeung-kim",
    "yunjae-gim",
    "seongyeong-kim",
    "soyeon-park",
    "zeho-oh",
    "jihoon-jung",
    "sieun-lee",
    "suhyeon-min",
    "sungkyeong-bae",
]

PART2_MEMBERS = [
    "yeji-kim",
    "jiwoo-yoon",
    "bonwook-gu",
    "sungmin-hwang",
    "soyeon-lee",
    "sooneun-bae",
    "dayeon-kang",
    "hyein-lee",
    "jooyoung-lee",
    "youlim-hong",
    "heejoon-kang",
    "chanho-ma",
    "juyoung-noh",
    "sulim-lee",
    "yoonjung-koo",
    "hyoeun-ji",
    "seonmin-lee",
    "heeseung-han",
    "yejin-moon" ,
    "subin-han" ,
    "subin-shin" ,
    "seungmin-lee",

]

STUDY_CONFIG = {
    "org_name": "oracleaistudy",
    "book_name": "혼자 공부하는 머신러닝 딥러닝",
    "part1_current_chapter": "8",
    "part2_current_chapter": "3",
    
}


# =============================
# 상세 챕터 구조 및 학습 내용 매핑
# =============================

CHAPTER_STRUCTURE = {
    'ch01': {
        'title': 'Chapter 01 - 나의 첫 머신러닝',
        'subtitle': '이 생선의 이름은 무엇인가요?',
        'sections': [
            {
                'id': '01-1',
                'title': '인공지능과 머신러닝, 딥러닝',
                'concepts': ['인공지능이란', '머신러닝이란', '딥러닝이란'],
                'keywords': ['인공지능', '머신러닝', '딥러닝', '특성', '레이블']
            },
            {
                'id': '01-2',
                'title': '코랩과 주피터 노트북',
                'concepts': ['구글 코랩', '텍스트 셀', '코드 셀', '노트북'],
                'keywords': ['Google Colab', 'Jupyter Notebook', '마크다운']
            },
            {
                'id': '01-3',
                'title': '마켓과 머신러닝',
                'concepts': ['생선 분류 문제', '첫 번째 머신러닝 프로그램'],
                'keywords': ['도미', '빙어', '산점도', 'k-최근접 이웃'],
                'practice': ['도미와 빙어 분류 실습']
            }
        ]
    },
    'ch02': {
        'title': 'Chapter 02 - 데이터 다루기',
        'subtitle': '수상한 생선을 조심하라!',
        'sections': [
            {
                'id': '02-1',
                'title': '훈련 세트와 테스트 세트',
                'concepts': ['지도 학습과 비지도 학습', '훈련 세트와 테스트 세트', '샘플링 편향', '넘파이'],
                'keywords': ['훈련 세트', '테스트 세트', '샘플링 편향', 'numpy'],
                'practice': ['train_test_split 활용', '모델 평가']
            },
            {
                'id': '02-2',
                'title': '데이터 전처리',
                'concepts': ['데이터 준비', '스케일링', '전처리의 중요성'],
                'keywords': ['StandardScaler', '표준화', '정규화', '전처리'],
                'practice': ['StandardScaler로 데이터 전처리', '스케일이 다른 특성 처리']
            }
        ]
    },
    'ch03': {
        'title': 'Chapter 03 - 회귀 알고리즘과 모델 규제',
        'subtitle': '농어의 무게를 예측하라!',
        'sections': [
            {
                'id': '03-1',
                'title': 'k-최근접 이웃 회귀',
                'concepts': ['회귀 문제', '결정계수(R²)', '과대적합 vs 과소적합'],
                'keywords': ['k-NN 회귀', 'R² 스코어', '과대적합', '과소적합'],
                'practice': ['KNeighborsRegressor', '회귀 모델 평가']
            },
            {
                'id': '03-2',
                'title': '선형 회귀',
                'concepts': ['선형 회귀', '다항 회귀'],
                'keywords': ['LinearRegression', '다항 회귀', '특성 공학'],
                'practice': ['선형 회귀 모델 훈련', 'PolynomialFeatures 생성']
            },
            {
                'id': '03-3',
                'title': '특성 공학과 규제',
                'concepts': ['다중 회귀', '규제', '릿지 회귀', '라쏘 회귀'],
                'keywords': ['다중 회귀', 'Ridge', 'Lasso', '규제', '과대적합 방지'],
                'practice': ['Ridge/Lasso 회귀', '규제 적용']
            }
        ]
    },
    'ch04': {
        'title': 'Chapter 04 - 다양한 분류 알고리즘',
        'subtitle': '럭키백의 확률을 계산하라!',
        'sections': [
            {
                'id': '04-1',
                'title': '로지스틱 회귀',
                'concepts': ['로지스틱 회귀', '시그모이드 함수', '확률 예측'],
                'keywords': ['LogisticRegression', '이진 분류', '다중 분류', '확률'],
                'practice': ['로지스틱 회귀로 확률 예측']
            },
            {
                'id': '04-2',
                'title': '확률적 경사 하강법',
                'concepts': ['점진적 학습', 'SGD', '에포크'],
                'keywords': ['SGDClassifier', '경사 하강법', '에포크', '학습률'],
                'practice': ['SGDClassifier 사용', '점진적 학습']
            }
        ]
    },
    'ch05': {
        'title': 'Chapter 05 - 트리 알고리즘',
        'subtitle': '화이트 와인을 찾아라!',
        'sections': [
            {
                'id': '05-1',
                'title': '결정 트리',
                'concepts': ['결정 트리 구조', '불순도', '정보 이득'],
                'keywords': ['DecisionTreeClassifier', '지니 불순도', '엔트로피'],
                'practice': ['결정 트리 모델 훈련', '트리 시각화']
            },
            {
                'id': '05-2',
                'title': '교차 검증과 그리드 서치',
                'concepts': ['검증 세트', '교차 검증', '하이퍼파라미터 튜닝'],
                'keywords': ['cross_validate', 'GridSearchCV', '하이퍼파라미터'],
                'practice': ['교차 검증', '그리드 서치로 최적 파라미터 탐색']
            },
            {
                'id': '05-3',
                'title': '트리의 앙상블',
                'concepts': ['랜덤 포레스트', '엑스트라 트리', '그레이디언트 부스팅'],
                'keywords': ['RandomForest', 'ExtraTrees', 'GradientBoosting', 'HistGradientBoosting'],
                'practice': ['앙상블 모델 구현', '특성 중요도 분석']
            }
        ]
    },
    'ch06': {
        'title': 'Chapter 06 - 비지도 학습',
        'subtitle': '비슷한 과일끼리 모으자!',
        'sections': [
            {
                'id': '06-1',
                'title': '군집 알고리즘',
                'concepts': ['비지도 학습', '군집화', '픽셀값 분석'],
                'keywords': ['군집', '비지도 학습', '클러스터'],
                'practice': ['이미지 데이터 군집화']
            },
            {
                'id': '06-2',
                'title': 'k-평균',
                'concepts': ['k-평균 알고리즘', '클러스터 중심', '엘보우 방법'],
                'keywords': ['KMeans', '클러스터 중심', '이너셔', '엘보우'],
                'practice': ['KMeans 클러스터링', '최적 k 찾기']
            },
            {
                'id': '06-3',
                'title': '주성분 분석',
                'concepts': ['차원 축소', 'PCA', '설명된 분산'],
                'keywords': ['PCA', '차원 축소', '주성분', '분산'],
                'practice': ['PCA 차원 축소', '원본 데이터 재구성']
            }
        ]
    },
    'ch07': {
        'title': 'Chapter 07 - 딥러닝을 시작합니다',
        'subtitle': '패션 럭키백을 판매합니다!',
        'sections': [
            {
                'id': '07-1',
                'title': '인공 신경망',
                'concepts': ['인공 신경망 구조', 'Dense Layer', '활성화 함수'],
                'keywords': ['인공 신경망', 'Dense', 'Sequential', 'ReLU', 'Softmax'],
                'practice': ['Sequential 모델 구성', 'Fashion MNIST 분류']
            },
            {
                'id': '07-2',
                'title': '심층 신경망',
                'concepts': ['은닉층', '렐루 활성화 함수', '옵티마이저'],
                'keywords': ['심층 신경망', 'ReLU', 'Adam', 'SGD 옵티마이저'],
                'practice': ['다층 신경망 구축', '옵티마이저 선택']
            },
            {
                'id': '07-3',
                'title': '신경망 모델 훈련',
                'concepts': ['손실 곡선', '검증 손실', '드롭아웃', '콜백'],
                'keywords': ['Dropout', 'EarlyStopping', 'ModelCheckpoint', '과대적합 방지'],
                'practice': ['드롭아웃 적용', '콜백 함수 사용', '모델 저장']
            }
        ]
    },
    'ch08': {
        'title': 'Chapter 08 - 이미지를 위한 인공 신경망',
        'subtitle': '패션 럭키백의 정확도를 높입니다!',
        'sections': [
            {
                'id': '08-1',
                'title': '합성곱 신경망의 구성 요소',
                'concepts': ['합성곱', '필터', '풀링'],
                'keywords': ['Conv2D', 'MaxPooling2D', '합성곱', '풀링'],
                'practice': ['합성곱 층 구성']
            },
            {
                'id': '08-2',
                'title': '합성곱 신경망을 사용한 이미지 분류',
                'concepts': ['CNN 모델 구축', '모델 컴파일과 훈련'],
                'keywords': ['CNN', '이미지 분류', 'Fashion MNIST'],
                'practice': ['CNN 모델 구현', 'Fashion MNIST 분류']
            },
            {
                'id': '08-3',
                'title': '합성곱 신경망의 시각화',
                'concepts': ['가중치 시각화', '함수형 API', '특성 맵'],
                'keywords': ['함수형 API', '특성 맵', '시각화'],
                'practice': ['필터 가중치 시각화', '특성 맵 시각화']
            }
        ]
    },
    'ch09': {
        'title': 'Chapter 09 - 텍스트를 위한 인공 신경망',
        'subtitle': '한빛 마켓의 댓글을 분석하라!',
        'sections': [
            {
                'id': '09-1',
                'title': '순차 데이터와 순환 신경망',
                'concepts': ['순차 데이터', '순환 신경망', 'RNN 셀'],
                'keywords': ['순차 데이터', 'RNN', '순환 신경망'],
                'practice': ['순환 신경망 이해']
            },
            {
                'id': '09-2',
                'title': '순환 신경망으로 IMDB 리뷰 분류하기',
                'concepts': ['IMDB 데이터셋', 'SimpleRNN', '단어 임베딩'],
                'keywords': ['SimpleRNN', 'Embedding', 'IMDB'],
                'practice': ['SimpleRNN 구현', 'IMDB 리뷰 분류']
            },
            {
                'id': '09-3',
                'title': 'LSTM과 GRU 셀',
                'concepts': ['LSTM 구조', 'GRU 구조', '드롭아웃', '다층 RNN'],
                'keywords': ['LSTM', 'GRU', '장단기 메모리'],
                'practice': ['LSTM 구현', 'GRU 구현', '다층 순환 신경망']
            }
        ]
    },
    'ch10': {
        'title': 'Chapter 10 - 언어 모델을 위한 신경망',
        'subtitle': '최신 언어 모델 이해하기',
        'sections': [
            {
                'id': '10-1',
                'title': '어텐션 메커니즘과 트랜스포머',
                'concepts': ['인코더-디코더', '어텐션 메커니즘', '트랜스포머', '셀프 어텐션'],
                'keywords': ['Attention', 'Transformer', '셀프 어텐션', '층 정규화'],
                'practice': ['트랜스포머 구조 이해']
            },
            {
                'id': '10-2',
                'title': '트랜스포머로 상품 설명 요약하기',
                'concepts': ['전이 학습', 'BART 모델', '허깅페이스', '토큰화'],
                'keywords': ['BART', 'KoBART', 'HuggingFace', '전이 학습'],
                'practice': ['KoBART 모델 로드', '텍스트 요약']
            },
            {
                'id': '10-3',
                'title': '대규모 언어 모델로 텍스트 생성하기',
                'concepts': ['LLM', 'EXAONE', 'GPT', 'OpenAI API'],
                'keywords': ['LLM', 'EXAONE', 'GPT', '토큰 디코딩'],
                'practice': ['EXAONE 사용', 'OpenAI API 활용']
            }
        ]
    }
}

# 스킬맵 상세 매핑 (소절 단위)
DETAILED_SKILL_MAPPING = {
    'ch01': {
        '데이터 전처리': 5,
        '머신러닝 기초': 15,
        'Git/GitHub': 3
    },
    'ch02': {
        '데이터 전처리': 20,
        '머신러닝 기초': 10,
        '모델 평가': 5,
        'Git/GitHub': 5
    },
    'ch03': {
        '머신러닝 기초': 15,
        '모델 평가': 15,
        '데이터 전처리': 5
    },
    'ch04': {
        '머신러닝 기초': 15,
        '모델 평가': 10
    },
    'ch05': {
        '머신러닝 기초': 15,
        '모델 평가': 15,
        '데이터 전처리': 5
    },
    'ch06': {
        '비지도 학습': 25,
        '데이터 전처리': 10
    },
    'ch07': {
        '딥러닝 기본': 20,
        '모델 평가': 5,
        'Git/GitHub': 3
    },
    'ch08': {
        'CNN': 25,
        '딥러닝 기본': 10
    },
    'ch09': {
        '딥러닝 기본': 15,
        'RNN': 20
    },
    'ch10': {
        '딥러닝 기본': 15,
        'Transformer': 25,
        'LLM': 10
    }
}

# 업데이트된 스킬 축 (RNN, Transformer, LLM 추가)
SKILL_AXES_DETAILED = [
    '데이터 전처리',
    '머신러닝 기초',
    '모델 평가',
    '비지도 학습',
    '딥러닝 기본',
    'CNN',
    'Git/GitHub'
]

def fetch_all_submissions():
    if not g:
        print("[ERROR] GitHub 연결 불가능 (토큰 없음)")
        return {}

    current_time = time.time()
    
    # 캐시 유효기간 내라면 캐시 반환
    if cache['submissions'] is not None and (current_time - cache['last_updated']) < cache['cache_duration']:
        return cache['submissions']
    
    submission_matrix = {}

    for repo_name, person_name in REPO_NAME_MAPPING.items():
        submission_matrix[repo_name] = {
            'name': person_name,
            'submissions': {},
            'total_completed': 0,
            'chapters': {},
        }
        for i in range(1, 11):
            ch_key = f'ch{i:02d}'
            submission_matrix[repo_name]['submissions'][ch_key] = {
                'completed': False,
                'url': None,
                'filename': None
            }
            submission_matrix[repo_name]['chapters'][ch_key] = False

    try:
        org = g.get_organization(STUDY_CONFIG['org_name'])
        repos = list(org.get_repos())

        for repo in repos:
            repo_name = repo.name

            if repo_name in REPO_NAME_MAPPING:
                try:
                    contents = repo.get_contents("")
                    files = [f for f in contents if not isinstance(f, dict)]
                    ipynb_files = [f for f in files if f.name.endswith('.ipynb')]

                    for file in ipynb_files:
                        detected_chapter = detect_chapter_from_filename(file.name)

                        if detected_chapter:
                            ch_key = detected_chapter
                            if not submission_matrix[repo_name]['submissions'][ch_key]['completed']:
                                submission_matrix[repo_name]['submissions'][ch_key] = {
                                    'completed': True,
                                    'url': file.html_url,
                                    'filename': file.name
                                }
                                submission_matrix[repo_name]['chapters'][ch_key] = True
                                submission_matrix[repo_name]['total_completed'] += 1

                except GithubException as e:
                    print(f"[ERROR] {repo_name}: {e.status}")
                except Exception as e:
                    print(f"[ERROR] {repo_name}: {str(e)}")

    except Exception as e:
        print(f"[ERROR] 조직 접근 실패: {str(e)}")

    cache['submissions'] = submission_matrix
    cache['last_updated'] = current_time

    return submission_matrix
    
def detect_chapter_from_filename(filename):
    """파일명에서 챕터 번호를 감지"""
    filename_lower = filename.lower()
    filename_clean = ''.join(
        c for c in filename_lower 
        if not ('\uac00' <= c <= '\ud7a3')
    )
    
    patterns = [
        (r'ch[_\-\s]?(\d{2})', '형식: ch01'),
        (r'chapter[_\-\s]?(\d{2})', '형식: chapter01'),
        (r'ch[_\-\s]?([1-9])(?![0-9])', '형식: ch1'),
        (r'chapter[_\-\s]?([1-9])(?![0-9])', '형식: chapter1'),
        (r'chap[_\-\s]?(\d{2})', '형식: chap01'),
        (r'chap[_\-\s]?([1-9])(?![0-9])', '형식: chap1'),
        (r'week[_\-\s]?(\d{2})', '형식: week01'),
        (r'week[_\-\s]?([1-9])(?![0-9])', '형식: week1'),
        (r'^(\d{1,2})[_\-\s]', '형식: 01-'),
        (r'^(\d{1,2})\.', '형식: 01.'),
    ]
    
    for pattern, pattern_desc in patterns:
        match = re.search(pattern, filename_clean)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 10:
                return f'ch{num:02d}'
    
    return None
# =============================
# 업데이트된 함수들
# =============================

def calculate_skill_scores_detailed(submissions_data):
    """
    상세 챕터 구조를 기반으로 스킬맵 점수 계산
    """
    skill_scores = {skill: 0 for skill in SKILL_AXES_DETAILED}
    
    for chapter_key, submission in submissions_data['submissions'].items():
        if submission['completed']:
            if chapter_key in DETAILED_SKILL_MAPPING:
                for skill, points in DETAILED_SKILL_MAPPING[chapter_key].items():
                    if skill in skill_scores:
                        skill_scores[skill] += points
    
    # 정규화 (0-100)
    max_scores = {
        '데이터 전처리': 45,
        '머신러닝 기초': 85,
        '모델 평가': 50,
        '비지도 학습': 25,
        '딥러닝 기본': 60,
        'CNN': 25,
        'Git/GitHub': 11
    }
    
    normalized_scores = {}
    for skill in SKILL_AXES_DETAILED:
        if skill in max_scores and max_scores[skill] > 0:
            normalized_scores[skill] = min(100, (skill_scores[skill] / max_scores[skill]) * 100)
        else:
            normalized_scores[skill] = 0
    
    return normalized_scores

def get_detailed_learning_profile(repo_name, submissions_data):
    """
    상세 학습 프로필 생성 (섹션별 정보 포함)
    """
    profile = {
        'name': submissions_data['name'],
        'repo_name': repo_name,
        'github_url': f"https://github.com/{STUDY_CONFIG['org_name']}/{repo_name}",
        'chapters': [],
        'skill_scores': calculate_skill_scores_detailed(submissions_data),
        'total_chapters': submissions_data['total_completed'],
        'completion_rate': round((submissions_data['total_completed'] / 10) * 100),
        'learned_concepts': [],
        'learned_keywords': []
    }
    
    # 챕터별 상세 정보
    for i in range(1, 11):
        ch_key = f'ch{i:02d}'
        submission = submissions_data['submissions'][ch_key]
        
        if ch_key in CHAPTER_STRUCTURE:
            chapter_info = CHAPTER_STRUCTURE[ch_key].copy()
            chapter_info['chapter_key'] = ch_key
            chapter_info['completed'] = submission['completed']
            chapter_info['url'] = submission.get('url')
            chapter_info['filename'] = submission.get('filename')
            
            if submission['completed']:
                # 학습한 개념과 키워드 수집
                for section in chapter_info['sections']:
                    profile['learned_concepts'].extend(section.get('concepts', []))
                    profile['learned_keywords'].extend(section.get('keywords', []))
            
            profile['chapters'].append(chapter_info)
    
    # 중복 제거
    profile['learned_concepts'] = list(set(profile['learned_concepts']))
    profile['learned_keywords'] = list(set(profile['learned_keywords']))
    
    return profile

def generate_detailed_weekly_report(repo_name, week_number, chapters):
    """
    주차별 상세 리포트 생성
    """
    submissions = fetch_all_submissions()
    
    if repo_name not in submissions:
        return None
    
    user_data = submissions[repo_name]
    
    learned_concepts = []
    learned_keywords = []
    code_practices = []
    completed_sections = []
    
    for ch_key in chapters:
        if user_data['submissions'][ch_key]['completed'] and ch_key in CHAPTER_STRUCTURE:
            chapter = CHAPTER_STRUCTURE[ch_key]
            
            for section in chapter['sections']:
                completed_sections.append({
                    'chapter': chapter['title'],
                    'section': section['title'],
                    'id': section['id']
                })
                learned_concepts.extend(section.get('concepts', []))
                learned_keywords.extend(section.get('keywords', []))
                code_practices.extend(section.get('practice', []))
    
    # AI 개인화 메시지 생성
    completed_count = len([ch for ch in chapters if user_data['submissions'][ch]['completed']])
    
    personalized_messages = [
        f"🎉 {user_data['name']}님, {week_number}주차에 {completed_count}개 챕터를 완료하셨네요! 머신러닝의 핵심 개념들을 차근차근 익혀가고 계십니다.",
        f"👏 훌륭해요! {user_data['name']}님은 이번 주 {len(learned_concepts)}개의 새로운 개념을 학습하셨어요. 꾸준한 학습 태도가 빛납니다!",
        f"💪 {user_data['name']}님의 실습 코드가 점점 완성도가 높아지고 있어요. 이론과 실습을 병행하는 학습 방식이 효과적입니다!",
        f"🚀 대단합니다! {user_data['name']}님은 이번 주 {len(code_practices)}개의 실습을 완료하셨어요. 실력이 빠르게 성장하고 있습니다!"
    ]
    
    import random
    personalized_message = random.choice(personalized_messages)
    
    # 학습 성과 요약
    performance_summary = f"{week_number}주차 동안 {len(completed_sections)}개 섹션을 완료하시며 "
    if completed_count == len(chapters):
        performance_summary += "목표한 모든 챕터를 달성하셨습니다! 🏆"
    elif completed_count >= len(chapters) * 0.7:
        performance_summary += "대부분의 학습 목표를 달성하셨습니다! 👍"
    else:
        performance_summary += "꾸준히 학습을 진행하고 계십니다. 계속 화이팅! 💪"
    
    report = {
        'user_name': user_data['name'],
        'week_number': week_number,
        'chapters': chapters,
        'completed_sections': completed_sections,
        'learned_concepts': list(set(learned_concepts)),
        'learned_keywords': list(set(learned_keywords)),
        'code_practices': list(set(code_practices)),
        'personalized_message': personalized_message,
        'performance_summary': performance_summary,
        'completed_count': completed_count,
        'total_count': len(chapters)
    }
    
    return report


def get_user_projects(user_name):
    """특정 사용자의 프로젝트 목록 가져오기"""
    if not supabase:
        return []
    
    try:
        response = supabase.table('portfolio_projects').select('*').eq('user_name', user_name).order('created_at', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[ERROR] 프로젝트 조회 실패: {e}")
        return []

# =========================
# 라우트 정의
# =========================

@app.route('/')
def index():
    """간소화된 메인 대시보드"""
    submissions = fetch_all_submissions()
    members_count = len(REPO_NAME_MAPPING)
    
    # PART별 분리
    part1_submissions = {k: v for k, v in submissions.items() if k in PART1_MEMBERS}
    part2_submissions = {k: v for k, v in submissions.items() if k in PART2_MEMBERS}
    
    # 현재 진행 챕터 (범위 지원)
    part1_current_str = STUDY_CONFIG.get('part1_current_chapter', '7')
    part2_current_str = STUDY_CONFIG.get('part2_current_chapter', '3')
    
    # 챕터 범위를 리스트로 변환하는 함수
    def parse_chapter_range(chapter_str):
        """
        '1-2' -> [1, 2]
        '6' -> [6]
        '3-4' -> [3, 4]
        """
        try:
            if '-' in chapter_str:
                start, end = chapter_str.split('-')
                return list(range(int(start), int(end) + 1))
            else:
                return [int(chapter_str)]
        except:
            return [1]
    
    part1_chapters = parse_chapter_range(part1_current_str)
    part2_chapters = parse_chapter_range(part2_current_str)
    
    # 마지막 챕터 번호 (제출률 계산용)
    part1_current_ch = max(part1_chapters)
    part2_current_ch = max(part2_chapters)
    
    # PART1 과제 제출 상태 (범위 내 모든 챕터 완료 여부)
    part1_submitted = 0
    for repo_name in PART1_MEMBERS:
        if repo_name in submissions:
            # 해당 범위의 모든 챕터를 완료했는지 확인
            all_completed = True
            for ch_num in part1_chapters:
                ch_key = f'ch{ch_num:02d}'
                if not submissions[repo_name]['submissions'][ch_key]['completed']:
                    all_completed = False
                    break
            
            if all_completed:
                part1_submitted += 1
    
    part1_submit_rate = round((part1_submitted / len(PART1_MEMBERS)) * 100) if PART1_MEMBERS else 0
    part1_not_submit_rate = 100 - part1_submit_rate
    
    # PART2 과제 제출 상태 (범위 내 모든 챕터 완료 여부)
    part2_submitted = 0
    for repo_name in PART2_MEMBERS:
        if repo_name in submissions:
            # 해당 범위의 모든 챕터를 완료했는지 확인
            all_completed = True
            for ch_num in part2_chapters:
                ch_key = f'ch{ch_num:02d}'
                if not submissions[repo_name]['submissions'][ch_key]['completed']:
                    all_completed = False
                    break
            
            if all_completed:
                part2_submitted += 1
    
    part2_submit_rate = round((part2_submitted / len(PART2_MEMBERS)) * 100) if PART2_MEMBERS else 0
    part2_not_submit_rate = 100 - part2_submit_rate
    
    # 전체 진행률 계산
    total_completed = sum(data['total_completed'] for data in submissions.values())
    total_possible = members_count * 10
    avg_progress = round((total_completed / total_possible) * 100) if total_possible > 0 else 0
    
    # PART별 TOP 3 완료자
    part1_top_users = sorted(
        part1_submissions.items(),
        key=lambda x: x[1]['total_completed'],
        reverse=True
    )[:3]
    
    part2_top_users = sorted(
        part2_submissions.items(),
        key=lambda x: x[1]['total_completed'],
        reverse=True
    )[:3]
    
    # PART별 평균 진행률
    part1_completed = sum(
        submissions[k]['total_completed'] 
        for k in PART1_MEMBERS if k in submissions
    )
    part1_avg = round((part1_completed / (len(PART1_MEMBERS) * 10)) * 100) if PART1_MEMBERS else 0
    
    part2_completed = sum(
        submissions[k]['total_completed'] 
        for k in PART2_MEMBERS if k in submissions
    )
    part2_avg = round((part2_completed / (len(PART2_MEMBERS) * 10)) * 100) if PART2_MEMBERS else 0
    
    # 챕터별 완료 현황 (차트용)
    chapter_stats = {}
    for i in range(1, 11):
        ch_key = f'ch{i:02d}'
        completed_count = sum(
            1 for data in submissions.values()
            if data['submissions'][ch_key]['completed']
        )
        chapter_stats[f'Ch{i:02d}'] = completed_count
    
    # PART별 퀴즈 TOP 3
    part1_quiz_top = []
    part2_quiz_top = []
    
    if supabase:
        try:
            response = supabase.table('quiz_completions').select('*').execute()
            user_counts = {}
            for record in response.data:
                user_name = record['user_name']
                user_counts[user_name] = user_counts.get(user_name, 0) + 1
            
            # PART1 멤버의 이름 목록 생성
            part1_names = [REPO_NAME_MAPPING[repo] for repo in PART1_MEMBERS if repo in REPO_NAME_MAPPING]
            part2_names = [REPO_NAME_MAPPING[repo] for repo in PART2_MEMBERS if repo in REPO_NAME_MAPPING]
            
            # PART별로 분리
            part1_counts = {name: count for name, count in user_counts.items() if name in part1_names}
            part2_counts = {name: count for name, count in user_counts.items() if name in part2_names}
            
            part1_quiz_top = sorted(part1_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            part2_quiz_top = sorted(part2_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        except:
            pass
    
    # 최근 논문 3개
    recent_papers = []
    if supabase:
        try:
            response = supabase.table('papers').select('*').order('created_at', desc=True).limit(3).execute()
            recent_papers = response.data
        except:
            pass
    

    
    return render_template('index.html',
                         members_count=members_count,
                         avg_progress=avg_progress,
                         part1_top_users=part1_top_users,
                         part2_top_users=part2_top_users,
                         part1_avg=part1_avg,
                         part2_avg=part2_avg,
                         chapter_stats=chapter_stats,
                         part1_submissions=part1_submissions,
                         part2_submissions=part2_submissions,
                         part1_quiz_top=part1_quiz_top,
                         part2_quiz_top=part2_quiz_top,
                         part1_submit_rate=part1_submit_rate,
                         part1_not_submit_rate=part1_not_submit_rate,
                         part2_submit_rate=part2_submit_rate,
                         part2_not_submit_rate=part2_not_submit_rate,
                         part1_current_ch=part1_current_str,
                         part2_current_ch=part2_current_str,
                         recent_papers=recent_papers,
                     )





@app.route('/progress')
def progress():
    """개인별 진도 페이지"""
    submissions = fetch_all_submissions()
    
    part1_submissions = {k: v for k, v in submissions.items() if k in PART1_MEMBERS}
    part2_submissions = {k: v for k, v in submissions.items() if k in PART2_MEMBERS}
    
    part1_sorted = dict(sorted(part1_submissions.items(), key=lambda x: x[1]['name']))
    part2_sorted = dict(sorted(part2_submissions.items(), key=lambda x: x[1]['name']))
    
    part1_chapter_stats = {}
    part2_chapter_stats = {}
    
    for i in range(1, 11):
        ch_key = f'ch{i:02d}'
        
        part1_count = sum(
            1 for k, data in part1_submissions.items()
            if data['submissions'][ch_key]['completed']
        )
        part1_chapter_stats[f'Ch{i:02d}'] = part1_count
        
        part2_count = sum(
            1 for k, data in part2_submissions.items()
            if data['submissions'][ch_key]['completed']
        )
        part2_chapter_stats[f'Ch{i:02d}'] = part2_count
    
    return render_template('progress.html',
                         part1_submissions=part1_sorted,
                         part2_submissions=part2_sorted,
                         part1_chapter_stats=part1_chapter_stats,
                         part2_chapter_stats=part2_chapter_stats)

@app.route('/quiz')
def quiz():
    return render_template('quiz.html', quizzes=QUIZZES)

@app.route('/papers')
def papers():
    """논문 게시판 페이지"""
    return render_template('papers.html')

@app.route('/papers/<int:paper_id>')
def paper_detail(paper_id):
    """논문 상세 페이지"""
    return render_template('paper_detail.html', paper_id=paper_id)

@app.route('/api/papers', methods=['GET'])
def get_papers():
    """논문 목록 조회"""
    try:
        if supabase:
            response = supabase.table('papers').select('*').order('created_at', desc=True).execute()
            return jsonify(response.data)
        else:
            return jsonify([]), 500
    except Exception as e:
        print(f"[ERROR] 논문 목록 조회 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/papers/<int:paper_id>', methods=['GET'])
def get_paper(paper_id):
    """논문 상세 조회"""
    try:
        if supabase:
            response = supabase.table('papers').select('*').eq('id', paper_id).execute()
            if response.data:
                return jsonify(response.data[0])
            return jsonify({'error': '논문을 찾을 수 없습니다'}), 404
        else:
            return jsonify({'error': 'Supabase 연결 없음'}), 500
    except Exception as e:
        print(f"[ERROR] 논문 조회 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/papers', methods=['POST'])
def create_paper():
    """논문 등록"""
    try:
        data = request.get_json()
        title = data.get('title')
        author = data.get('author')
        content = data.get('content')
        link = data.get('link')
        
        if not title or not author:
            return jsonify({'error': '제목과 작성자는 필수입니다'}), 400
        
        if supabase:
            response = supabase.table('papers').insert({
                'title': title,
                'author': author,
                'content': content,
                'link': link
            }).execute()
            return jsonify({'success': True, 'data': response.data})
        else:
            return jsonify({'error': 'Supabase 연결 없음'}), 500
            
    except Exception as e:
        print(f"[ERROR] 논문 등록 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/papers/<int:paper_id>/comments', methods=['GET'])
def get_comments(paper_id):
    """댓글 목록 조회"""
    try:
        if supabase:
            response = supabase.table('comments').select('*').eq('paper_id', paper_id).order('created_at', desc=False).execute()
            return jsonify(response.data)
        else:
            return jsonify([]), 500
    except Exception as e:
        print(f"[ERROR] 댓글 조회 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/papers/<int:paper_id>/comments', methods=['POST'])
def create_comment(paper_id):
    """댓글 작성"""
    try:
        data = request.get_json()
        author = data.get('author')
        content = data.get('content')
        
        if not author or not content:
            return jsonify({'error': '작성자와 내용은 필수입니다'}), 400
        
        if supabase:
            response = supabase.table('comments').insert({
                'paper_id': paper_id,
                'author': author,
                'content': content
            }).execute()
            return jsonify({'success': True, 'data': response.data})
        else:
            return jsonify({'error': 'Supabase 연결 없음'}), 500
            
    except Exception as e:
        print(f"[ERROR] 댓글 작성 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500
@app.route('/debug')
def debug():
    submissions = fetch_all_submissions()
    debug_info = []
    
    for repo_name, data in submissions.items():
        user_debug = {
            'name': data['name'],
            'repo_name': repo_name,
            'total': data['total_completed'],
            'files': []
        }
        
        for chapter_key, submission in data['submissions'].items():
            if submission['completed'] and submission.get('filename'):
                user_debug['files'].append({
                    'original_filename': submission['filename'],
                    'detected_chapter': detect_chapter_from_filename(submission['filename']),
                    'chapter_key': chapter_key,
                    'url': submission['url']
                })
        
        debug_info.append(user_debug)
    
    return render_template('debug.html', debug_info=debug_info)

# API 라우트
@app.route('/api/users')
def get_users():
    users = list(REPO_NAME_MAPPING.values())
    return jsonify(sorted(users))

@app.route('/api/quiz-stats')
def quiz_stats():
    try:
        if supabase:
            response = supabase.table('quiz_completions').select('*').execute()
            stats = {}
            
            for chapter, quiz_list in QUIZZES.items():
                for quiz in quiz_list:
                    quiz_id = quiz['id']
                    completed_users = [
                        record['user_name'] 
                        for record in response.data 
                        if record['quiz_id'] == quiz_id
                    ]
                    
                    stats[quiz_id] = {
                        'completed': len(completed_users),
                        'users': completed_users
                    }
            
            return jsonify(stats)
        else:
            quiz_results = load_quiz_results()
            stats = {}
            
            for chapter, quiz_list in QUIZZES.items():
                for quiz in quiz_list:
                    quiz_id = quiz['id']
                    completed_users = [user for user in quiz_results.keys() 
                                      if quiz_id in quiz_results[user].get('completed_quizzes', [])]
                    stats[quiz_id] = {
                        'completed': len(completed_users),
                        'users': completed_users
                    }
            
            return jsonify(stats)
    
    except Exception as e:
        print(f"[ERROR] 퀴즈 통계 조회 실패: {str(e)}")
        return jsonify({}), 500

@app.route('/api/quiz-complete', methods=['POST'])
def quiz_complete():
    try:
        data = request.get_json()
        user_name = data.get('user_name')
        quiz_id = data.get('quiz_id')
        
        if not user_name or not quiz_id:
            return jsonify({'error': '필수 정보 누락'}), 400
        
        if supabase:
            response = supabase.table('quiz_completions').upsert({
                'user_name': user_name,
                'quiz_id': quiz_id,
                'completed_at': datetime.now().isoformat()
            }).execute()
        else:
            quiz_results = load_quiz_results()
            
            if user_name not in quiz_results:
                quiz_results[user_name] = {'completed_quizzes': []}
            
            if quiz_id not in quiz_results[user_name]['completed_quizzes']:
                quiz_results[user_name]['completed_quizzes'].append(quiz_id)
            
            save_quiz_results(quiz_results)
        
        return jsonify({'success': True})
    
    except Exception as e:
        print(f"[ERROR] 퀴즈 완료 기록 실패: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/quiz-leaderboard')
def quiz_leaderboard():
    try:
        if supabase:
            response = supabase.table('quiz_completions').select('*').execute()
            user_counts = {}
            for record in response.data:
                user_name = record['user_name']
                user_counts[user_name] = user_counts.get(user_name, 0) + 1
        else:
            quiz_results = load_quiz_results()
            user_counts = {
                user: len(data.get('completed_quizzes', []))
                for user, data in quiz_results.items()
            }
        
        leaderboard = sorted(
            user_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return jsonify([
            {'rank': idx + 1, 'name': name, 'completed': count}
            for idx, (name, count) in enumerate(leaderboard)
        ])
    
    except Exception as e:
        print(f"[ERROR] 리더보드 조회 실패: {str(e)}")
        return jsonify([]), 500

@app.route('/api/refresh-cache', methods=['POST'])
def refresh_cache():
    cache['submissions'] = None
    cache['last_updated'] = 0
    fetch_all_submissions()
    return jsonify({'success': True, 'message': 'Cache refreshed'})

@app.route('/ranking')
def ranking():
    """종합 랭킹 페이지"""
    submissions = fetch_all_submissions()
    
    # 전체 랭킹 계산
    rankings = []
    for repo_name, data in submissions.items():
        name = data['name']
        chapter_score = data['total_completed'] * 10
        
        # 퀴즈 점수 및 개수
        quiz_count = 0
        quiz_score = 0
        if supabase:
            try:
                response = supabase.table('quiz_completions').select('*').eq('user_name', name).execute()
                quiz_count = len(response.data)
                quiz_score = quiz_count * 5
            except:
                pass
        
        # 논문 점수 및 개수
        paper_count = 0
        paper_score = 0
        if supabase:
            try:
                response = supabase.table('papers').select('*').eq('author', name).execute()
                paper_count = len(response.data)
                paper_score = paper_count * 2
            except:
                pass
        
        total_score = chapter_score + quiz_score + paper_score
        
        
        # 뱃지 계산
        badges = []
        
        # 💎 완벽주의자: 전체 챕터 완료
        if data['total_completed'] >= 10:
            badges.append({'icon': '💎', 'name': '완벽주의자'})
        
        # 🎯 퀴즈 마스터: 퀴즈 10개 이상 완료
        if quiz_count >= 10:
            badges.append({'icon': '🎯', 'name': '퀴즈 마스터'})
        
        # 📚 북웜: 논문 공유 5회 이상
        if paper_count >= 5:
            badges.append({'icon': '📚', 'name': '북웜'})
        
        # 🥇 골드 러너: 6챕터 이상 완료
        if data['total_completed'] >= 6:
            badges.append({'icon': '🥇', 'name': '골드 러너'})
        
        # 🔥 불꽃 학습자: 3챕터 이상 완료
        if data['total_completed'] >= 3:
            badges.append({'icon': '🔥', 'name': '불꽃 학습자'})
        
        
        # 레벨 계산
        if total_score >= 150:
            level = "🏆 그랜드 마스터"
            level_color = "#FFD700"
        elif total_score >= 100:
            level = "💎 마스터"
            level_color = "#C0C0C0"
        elif total_score >= 70:
            level = "⭐ 전문가"
            level_color = "#CD7F32"
        elif total_score >= 40:
            level = "🔥 열정적인 학습자"
            level_color = "#FF6B6B"
        else:
            level = "🌱 초보 학습자"
            level_color = "#51CF66"
        
        rankings.append({
            'name': name,
            'repo_name': repo_name,
            'total_score': total_score,
            'chapter_score': chapter_score,
            'quiz_score': quiz_score,
            'paper_score': paper_score,
            'quiz_count': quiz_count,
            'paper_count': paper_count,
            'badges': badges,
            'level': level,
            'level_color': level_color,
            'chapters_completed': data['total_completed'],
        })
    
    # 점수순 정렬
    rankings.sort(key=lambda x: x['total_score'], reverse=True)
    
    # 순위 부여 (동점 처리)
    current_rank = 0
    prev_score = None
    for idx, data in enumerate(rankings, start=1):
        if data['total_score'] != prev_score:
            current_rank = idx
            prev_score = data['total_score']
        data['rank'] = current_rank
    
    # TOP 3 순위별 그룹 생성
    top_ranks = {}
    for rank_data in rankings:
        rank = rank_data['rank']
        if rank <= 3:
            if rank not in top_ranks:
                top_ranks[rank] = []
            top_ranks[rank].append(rank_data)
    
    return render_template('ranking.html', 
                         rankings=rankings,
                         top_ranks=top_ranks)

# =============================
# 업데이트된 라우트
# =============================

@app.route('/portfolio')
def portfolio():
    """포트폴리오 메인 페이지"""
    submissions = fetch_all_submissions()
    
    # 디버깅
    print(f"=== Portfolio Debug ===")
    print(f"Total submissions: {len(submissions)}")
    print(f"PART1_MEMBERS count: {len(PART1_MEMBERS)}")
    print(f"PART2_MEMBERS count: {len(PART2_MEMBERS)}")
    
    # Part1 멤버
    part1_members = []
    for repo_name in PART1_MEMBERS:
        if repo_name in submissions:
            data = submissions[repo_name]
            skill_scores = calculate_skill_scores_detailed(data)
            avg_skill = sum(skill_scores.values()) / len(skill_scores) if skill_scores else 0
            
            part1_members.append({
                'repo_name': repo_name,
                'name': data['name'],
                'total_completed': data['total_completed'],
                'avg_skill_score': round(avg_skill, 1),
                'github_url': f"https://github.com/{STUDY_CONFIG['org_name']}/{repo_name}",
                'profile_url': f"/portfolio/{repo_name}"
            })
    
    part1_members.sort(key=lambda x: x['name'])
    
    # Part2 멤버
    part2_members = []
    for repo_name in PART2_MEMBERS:
        if repo_name in submissions:
            data = submissions[repo_name]
            skill_scores = calculate_skill_scores_detailed(data)
            avg_skill = sum(skill_scores.values()) / len(skill_scores) if skill_scores else 0
            
            part2_members.append({
                'repo_name': repo_name,
                'name': data['name'],
                'total_completed': data['total_completed'],
                'avg_skill_score': round(avg_skill, 1),
                'github_url': f"https://github.com/{STUDY_CONFIG['org_name']}/{repo_name}",
                'profile_url': f"/portfolio/{repo_name}"
            })
    
    part2_members.sort(key=lambda x: x['name'])
    
    return render_template('portfolio.html', 
                         part1_members=part1_members, 
                         part2_members=part2_members,
                         book_name=STUDY_CONFIG['book_name'])

@app.route('/portfolio/<repo_name>')
def portfolio_detail(repo_name):
    """개인 포트폴리오 상세 페이지"""
    submissions = fetch_all_submissions()
    
    if repo_name not in submissions:
        return "사용자를 찾을 수 없습니다", 404
    
    profile = get_detailed_learning_profile(repo_name, submissions[repo_name])
    
    # 퀴즈 완료 개수
    quiz_count = 0
    if supabase:
        try:
            response = supabase.table('quiz_completions').select('*').eq('user_name', profile['name']).execute()
            quiz_count = len(response.data)
        except:
            pass
    
    profile['quiz_count'] = quiz_count
    
    return render_template('portfolio_detail.html', 
                         profile=profile, 
                         skill_axes=SKILL_AXES_DETAILED,
                         chapter_structure=CHAPTER_STRUCTURE)

@app.route('/portfolio/<repo_name>/report/<int:week>')
def weekly_report(repo_name, week):
    """주차별 학습 리포트"""
    # 주차별 챕터 매핑 (예시)
    week_chapters_map = {
        1: ['ch01', 'ch02'],
        2: ['ch03'],
        3: ['ch04'],
        4: ['ch05'],
        5: ['ch06'],
        6: ['ch07'],
        7: ['ch08'],
        8: ['ch09'],
        9: ['ch10']
    }
    
    if week not in week_chapters_map:
        return "해당 주차가 존재하지 않습니다", 404
    
    chapters = week_chapters_map[week]
    report = generate_detailed_weekly_report(repo_name, week, chapters)
    
    if not report:
        return "리포트를 생성할 수 없습니다", 404
    
    return render_template('weekly_report_detailed.html', 
                         report=report, 
                         repo_name=repo_name,
                         week=week)

@app.route('/api/skill-comparison')
def skill_comparison():
    """전체 스터디원 스킬 비교 API"""
    submissions = fetch_all_submissions()
    
    comparison_data = []
    for repo_name, data in submissions.items():
        skill_scores = calculate_skill_scores_detailed(data)
        comparison_data.append({
            'name': data['name'],
            'repo_name': repo_name,
            'skills': skill_scores
        })
    
    return jsonify({
        'members': comparison_data,
        'axes': SKILL_AXES_DETAILED
    })


@app.route('/api/projects/<repo_name>', methods=['GET'])
def get_projects_api(repo_name):
    """특정 사용자의 프로젝트 목록 API"""
    submissions = fetch_all_submissions()
    
    if repo_name not in submissions:
        return jsonify({'error': '사용자를 찾을 수 없습니다'}), 404
    
    user_name = submissions[repo_name]['name']
    projects = get_user_projects(user_name)
    
    return jsonify({
        'user_name': user_name,
        'projects': projects
    })

@app.route('/api/projects/<repo_name>', methods=['POST'])
def add_project_api(repo_name):
    """프로젝트 추가 API"""
    if not supabase:
        return jsonify({'error': 'Supabase 연결 실패'}), 500
    
    submissions = fetch_all_submissions()
    
    if repo_name not in submissions:
        return jsonify({'error': '사용자를 찾을 수 없습니다'}), 404
    
    user_name = submissions[repo_name]['name']
    data = request.json
    
    project_data = {
        'user_name': user_name,
        'title': data.get('title'),
        'description': data.get('description'),
        'notion_url': data.get('notion_url'),
        'github_url': data.get('github_url'),
        'demo_url': data.get('demo_url'),
        'status': data.get('status', '진행중'),
        'start_date': data.get('start_date'),
        'end_date': data.get('end_date'),
        'tech_stack': data.get('tech_stack', []),
        'tags': data.get('tags', [])
    }
    
    try:
        response = supabase.table('portfolio_projects').insert(project_data).execute()
        return jsonify({'success': True, 'project': response.data[0]})
    except Exception as e:
        print(f"[ERROR] 프로젝트 추가 실패: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<repo_name>/<project_id>', methods=['PUT'])
def update_project_api(repo_name, project_id):
    """프로젝트 수정 API"""
    if not supabase:
        return jsonify({'error': 'Supabase 연결 실패'}), 500
    
    data = request.json
    
    update_data = {}
    if 'status' in data:
        update_data['status'] = data['status']
    if 'notion_url' in data:
        update_data['notion_url'] = data['notion_url']
    if 'github_url' in data:
        update_data['github_url'] = data['github_url']
    if 'demo_url' in data:
        update_data['demo_url'] = data['demo_url']
    if 'end_date' in data:
        update_data['end_date'] = data['end_date']
    
    try:
        # ✅ 여기 수정: projects → portfolio_projects
        response = supabase.table('portfolio_projects').update(update_data).eq('id', project_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] 프로젝트 수정 실패: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<repo_name>/<project_id>', methods=['DELETE'])
def delete_project_api(repo_name, project_id):
    """프로젝트 삭제 API"""
    if not supabase:
        return jsonify({'error': 'Supabase 연결 실패'}), 500
    
    try:
        # ✅ 여기 수정: projects → portfolio_projects
        response = supabase.table('portfolio_projects').delete().eq('id', project_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] 프로젝트 삭제 실패: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n=== 등록된 라우트 ===")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    print("=" * 40 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)