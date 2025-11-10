from flask import Flask, render_template, jsonify, request
from github import Github, GithubException
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import re
import time

# 로컬 개발 환경 지원
if os.path.exists('.env'):
    load_dotenv()

# Render 환경 변수도 지원
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

app = Flask(__name__)

# GitHub 토큰 설정 (환경 변수에서 직접 읽기)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or os.getenv('GITHUB_TOKEN_BACKUP')

print(f"\n{'='*60}")
print("[INIT] GitHub 토큰 확인")
print(f"  토큰: {GITHUB_TOKEN[:20] if GITHUB_TOKEN else 'None'}...")

if GITHUB_TOKEN:
    try:
        g = Github(GITHUB_TOKEN)
        # 연결 테스트
        g.get_user().login
        print(f"  ✓ GitHub 연결 성공")
    except Exception as e:
        print(f"  ✗ GitHub 연결 실패: {str(e)}")
        g = None
else:
    g = None
    print(f"  [WARNING] GitHub API 사용 불가")
print(f"{'='*60}\n")

QUIZ_DATA_FILE = 'quiz_results.json'

cache = {
    'submissions': None,
    'last_updated': 0,
    'cache_duration': 300
}

# ✅ QUIZZES: 딕셔너리 형식 유지 (리스트 아님)
QUIZZES = {
    # Ch01 - 여러 개 퀴즈
    "ch01": [
        {
            "id": "ch01",
            "title": "Ch01-1 - 머신러닝 개요",
            "gemini_link": "https://gemini.google.com/share/cd026cf98350"
        },
       
    ],
    
    # Ch02
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
    
    # 나머지도 같은 방식
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
    ]
    # ... ch04~ch10도 계속
}

# 레포지토리 이름과 사람 정보 매핑
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
    "jihoon-jeong": "정지훈",
    "sieun-lee": "이시은",
    "suhyeon-min": "민수현",
    "sungkyeong-bae": "배성경",
    "jiwoo-yoon": "윤지우",
    "bonwook-gu": "구본욱",
    "sungmin-hwang": "황성민",
    "soyeon-lee": "이소연",
    "sooneun-bae": "배순은",
    "dayeon-kang": "강다연",
    "haeyin-lee": "이혜인",
    "jooyoung-lee": "이주영",

    


}

# PART1: 기존 멤버 (8명)
PART1_MEMBERS = [
    "minjeong-ko", 
    "hagyeong-lee",
    "yeonseok-kim",
    "eunyong-choi",
    "sujeung-kim",
    "yunjae-gim",
    "seongyeong-kim",
    "soyeon-park",
    "zeho-oh",
    "jihoon-jeong",
    "sieun-lee",
    "suhyeon-min",
    "sungkyeong-bae",
    "suhyeon-min",
    
]

# PART2: 기존 + 새로운 멤버 (8명)
PART2_MEMBERS = [
    
    "yeji-kim",
    "jiwoo-yoon",
    "bonwook-gu",
    "sungmin-hwang",
    "soyeon-lee",
    "sooneun-bae",
    "dayeon-kang",
    "haeyin-lee",
    "jooyoung-lee"

]


STUDY_CONFIG = {
    "org_name": "oracleaistudy",
    "book_name": "혼자 공부하는 머신러닝 딥러닝",
    "part1_current_chapter": "6",      # PART1 현재 진행 챕터
    "part2_current_chapter": "1-2",  # PART2 현재 진행 챕터
}

def detect_chapter_from_filename(filename):
    """파일명에서 챕터 번호를 감지"""
    filename_lower = filename.lower()
    
    # 한글 문자 제거
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

def load_quiz_results():
    if os.path.exists(QUIZ_DATA_FILE):
        with open(QUIZ_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_quiz_results(data):
    with open(QUIZ_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_all_submissions():
    """GitHub 조직 내 레포지토리에서 제출 현황 수집"""
    
    if not g:
        print("[ERROR] GitHub 연결 불가능 (토큰 없음)")
        return {}
    
    current_time = time.time()
    
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
                    files = [f for f in contents if isinstance(f, dict) == False]
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

@app.route('/')
def index():
    submissions = fetch_all_submissions()
    members_count = len(REPO_NAME_MAPPING)
    
    # PART1과 PART2로 분리
    part1_submissions = {k: v for k, v in submissions.items() if k in PART1_MEMBERS}
    part2_submissions = {k: v for k, v in submissions.items() if k in PART2_MEMBERS}
    
    # 이름순 정렬
    part1_sorted = dict(sorted(part1_submissions.items(), key=lambda x: x[1]['name']))
    part2_sorted = dict(sorted(part2_submissions.items(), key=lambda x: x[1]['name']))
    
    return render_template('index.html',
                         members_count=members_count,
                         part1_submissions=part1_sorted,
                         part2_submissions=part2_sorted,
                         part1_current=STUDY_CONFIG['part1_current_chapter'],
                         part2_current=STUDY_CONFIG['part2_current_chapter'])

@app.route('/progress')  # ← 이 위치가 중요
def progress():
    submissions = fetch_all_submissions()
    
    part1_submissions = {k: v for k, v in submissions.items() if k in PART1_MEMBERS}
    part2_submissions = {k: v for k, v in submissions.items() if k in PART2_MEMBERS}
    
    part1_sorted = dict(sorted(part1_submissions.items(), key=lambda x: x[1]['name']))
    part2_sorted = dict(sorted(part2_submissions.items(), key=lambda x: x[1]['name']))
    
    return render_template('progress.html',
                         part1_submissions=part1_sorted,
                         part2_submissions=part2_sorted,
                         current_progress=10)


@app.route('/quiz')
def quiz():
    return render_template('quiz.html', quizzes=QUIZZES)

@app.route('/api/quiz-stats')
def quiz_stats():
    """퀴즈 통계"""
    quiz_results = load_quiz_results()
    stats = {}
    
    for chapter, quiz_list in QUIZZES.items():
        for quiz in quiz_list:
            quiz_id = quiz['id']
            # 완료한 사람 이름과 수 구하기
            completed_users = [user for user in quiz_results.keys() 
                              if quiz_id in quiz_results[user].get('completed_quizzes', [])]
            stats[quiz_id] = {
                'completed': len(completed_users),
                'users': completed_users  # 이름 목록 추가
            }
    
    return jsonify(stats)


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

@app.route('/api/refresh-cache', methods=['POST'])
def refresh_cache():
    cache['submissions'] = None
    cache['last_updated'] = 0
    fetch_all_submissions()
    return jsonify({'success': True, 'message': 'Cache refreshed'})
@app.route('/api/users')
def get_users():
    """한글 이름 목록 조회"""
    users = list(REPO_NAME_MAPPING.values())
    return jsonify(sorted(users))

@app.route('/api/quiz-complete', methods=['POST'])
def quiz_complete():
    """퀴즈 완료 기록"""
    data = request.get_json()
    user_name = data.get('user_name')
    quiz_id = data.get('quiz_id')
    
    if not user_name or not quiz_id:
        return jsonify({'error': '필수 정보 누락'}), 400
    
    quiz_results = load_quiz_results()
    
    if user_name not in quiz_results:
        quiz_results[user_name] = {'completed_quizzes': []}
    
    if quiz_id not in quiz_results[user_name]['completed_quizzes']:
        quiz_results[user_name]['completed_quizzes'].append(quiz_id)
    
    save_quiz_results(quiz_results)
    
    return jsonify({'success': True})


if __name__ == '__main__':
    # 등록된 라우트 출력
    print("\n=== 등록된 라우트 ===")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    print("=" * 40 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)