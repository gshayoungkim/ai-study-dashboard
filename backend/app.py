from flask import Flask, render_template, jsonify, request
from github import Github, GithubException
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import re
import time

# .env 파일 로드
load_dotenv()

app = Flask(__name__)

# GitHub 토큰 설정
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

print(f"\n{'='*60}")
print("[INIT] GitHub 토큰 확인")
if GITHUB_TOKEN:
    print(f"  토큰: {GITHUB_TOKEN[:20]}...***")
    g = Github(GITHUB_TOKEN)
    print(f"  ✓ GitHub 연결 성공")
else:
    print(f"  토큰: 없음 ❌")
    g = None
    print(f"  [WARNING] GitHub API 사용 불가")
print(f"{'='*60}\n")

QUIZ_DATA_FILE = 'quiz_results.json'

cache = {
    'submissions': None,
    'last_updated': 0,
    'cache_duration': 300
}

QUIZZES = {
    "ch01": {"title": "Ch01 - 머신러닝 개요", "gemini_link": "https://gemini.google.com/"},
    "ch02": {"title": "Ch02 - 데이터 전처리", "gemini_link": "https://gemini.google.com/"},
    "ch03": {"title": "Ch03 - 회귀", "gemini_link": "https://gemini.google.com/"},
    "ch04": {"title": "Ch04 - 분류", "gemini_link": "https://gemini.google.com/"},
    "ch05": {"title": "Ch05 - 모델 평가", "gemini_link": "https://gemini.google.com/share/58b3bbcd177d"},
    #"ch06": {"title": "Ch06 - 앙상블", "gemini_link": "https://gemini.google.com/"},
    #"ch07": {"title": "Ch07 - 신경망", "gemini_link": "https://gemini.google.com/"},
    #"ch08": {"title": "Ch08 - CNN", "gemini_link": "https://gemini.google.com/"},
    #"ch09": {"title": "Ch09 - RNN", "gemini_link": "https://gemini.google.com/"},
    #"ch10": {"title": "Ch10 - 고급 기법", "gemini_link": "https://gemini.google.com/"},
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
        "SIEUN-LEE": "이시은",
        "suhyeon-min": "민수현",
        "sungkyeong-bae": "배성경",
        "eunyong-choi": "최은용"
    }
STUDY_CONFIG = {
    "org_name": "oracleaistudy",
    "book_name": "혼자 공부하는 머신러닝 딥러닝",
    "current_progress": 10,
}

def detect_chapter_from_filename(filename):
    """파일명에서 챕터 번호를 감지 (매우 유연한 패턴)"""
    filename_lower = filename.lower()
    
    # 한글 문자 제거
    filename_clean = ''.join(
        c for c in filename_lower 
        if not ('\uac00' <= c <= '\ud7a3')
    )
    
    print(f"[DEBUG] '{filename}' → '{filename_clean}'")
    
    # 패턴들 (순서대로 시도)
    patterns = [
        # ch 형식: ch01, ch_01, ch-01, ch 01
        (r'ch[_\-\s]?(\d{2})', '형식: ch01'),
        (r'chapter[_\-\s]?(\d{2})', '형식: chapter01'),
        (r'ch[_\-\s]?([1-9])(?![0-9])', '형식: ch1'),
        (r'chapter[_\-\s]?([1-9])(?![0-9])', '형식: chapter1'),
        
        # chap 형식 (최은용처럼)
        (r'chap[_\-\s]?(\d{2})', '형식: chap01'),
        (r'chap[_\-\s]?([1-9])(?![0-9])', '형식: chap1'),
        
        # week 형식
        (r'week[_\-\s]?(\d{2})', '형식: week01'),
        (r'week[_\-\s]?([1-9])(?![0-9])', '형식: week1'),
        
        # 숫자만: 01-1, 02-3 등 (고민정처럼)
        (r'^(\d{1,2})[_\-\s]', '형식: 01-'),
        (r'^(\d{1,2})\.', '형식: 01.'),
    ]
    
    for pattern, pattern_desc in patterns:
        match = re.search(pattern, filename_clean)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 10:
                chapter = f'ch{num:02d}'
                print(f"  ✓ 감지됨: {chapter} ({pattern_desc})")
                return chapter
    
    print(f"  ✗ 감지 실패")
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
        print(f"[CACHE] Using cached data")
        return cache['submissions']
    
    print(f"\n{'='*60}")
    print("[GITHUB] GitHub에서 데이터 수집 중...")
    print(f"{'='*60}")
    
    submission_matrix = {}
    
    # 레포 이름 기준으로 초기화
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
        print(f"\n[1] 조직 정보 수집: {STUDY_CONFIG['org_name']}")
        org = g.get_organization(STUDY_CONFIG['org_name'])
        print(f"  ✓ 조직 찾음")
        
        print(f"\n[2] 조직 내 레포지토리 검색 중...")
        repos = list(org.get_repos())
        print(f"  ✓ 총 {len(repos)}개 레포지토리 찾음")
        
        for repo in repos:
            repo_name = repo.name  # 레포지토리 이름 (소유자 X)
            print(f"\n  [{repo_name}] 확인 중...")
            
            if repo_name in REPO_NAME_MAPPING:
                person_name = REPO_NAME_MAPPING[repo_name]
                print(f"    → {person_name}")
                
                try:
                    contents = repo.get_contents("")
                    files = [f for f in contents if isinstance(f, dict) == False]
                    
                    ipynb_files = [f for f in files if f.name.endswith('.ipynb')]
                    print(f"      → .ipynb 파일: {len(ipynb_files)}개")
                    
                    detected_count = 0
                    for file in ipynb_files:
                        detected_chapter = detect_chapter_from_filename(file.name)
                        
                        if detected_chapter:
                            detected_count += 1
                            ch_key = detected_chapter
                            if not submission_matrix[repo_name]['submissions'][ch_key]['completed']:
                                submission_matrix[repo_name]['submissions'][ch_key] = {
                                    'completed': True,
                                    'url': file.html_url,
                                    'filename': file.name
                                }
                                submission_matrix[repo_name]['chapters'][ch_key] = True
                                submission_matrix[repo_name]['total_completed'] += 1
                                print(f"        ✓ {file.name} → {ch_key}")
                    
                    print(f"      → 감지된 파일: {detected_count}개")
                
                except GithubException as e:
                    print(f"    ✗ GitHub 에러: {e.status} - {e.data.get('message', 'Unknown error')}")
                except Exception as e:
                    print(f"    ✗ 에러: {str(e)}")
            else:
                print(f"    → 스킵 (목록에 없음: {repo_name})")
    
    except GithubException as e:
        print(f"[ERROR] GitHub API 에러")
        print(f"  상태: {e.status}")
        print(f"  메시지: {e.data}")
    except Exception as e:
        print(f"[ERROR] 예상치 못한 에러: {str(e)}")
        import traceback
        traceback.print_exc()
    
    cache['submissions'] = submission_matrix
    cache['last_updated'] = current_time
    
    print(f"\n{'='*60}")
    print("[완료] 데이터 수집 완료")
    total_files = sum(d['total_completed'] for d in submission_matrix.values())
    print(f"  → 총 {total_files}개 파일 감지")
    print(f"{'='*60}\n")
    
    return submission_matrix

@app.route('/')
def index():
    submissions = fetch_all_submissions()
    members_count = len(REPO_NAME_MAPPING)
    
    return render_template('index.html',
                         members_count=members_count,
                         submissions=submissions,
                         current_progress=10)

@app.route('/progress')
def progress():
    submissions = fetch_all_submissions()
    sorted_submissions = dict(sorted(submissions.items(), key=lambda x: x[1]['name']))
    return render_template('progress.html',
                         submissions=sorted_submissions,
                         current_progress=10)

@app.route('/quiz')
def quiz():
    return render_template('quiz.html', quizzes=QUIZZES)
@app.route('/api/quiz-stats')
def quiz_stats():
    """퀴즈 통계"""
    quiz_results = load_quiz_results()
    stats = {}
    
    # 모든 퀴즈 ID에 대해 통계 생성
    for chapter, quiz_list in QUIZZES.items():
        for quiz in quiz_list:
            quiz_id = quiz['id']
            # 완료한 사람 수 세기
            count = sum(1 for user in quiz_results.values() 
                       if quiz_id in user.get('completed_quizzes', []))
            stats[quiz_id] = {
                'completed': count,
                'total': len(REPO_NAME_MAPPING)
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
                detected_chapter = detect_chapter_from_filename(submission['filename'])
                user_debug['files'].append({
                    'original_filename': submission['filename'],
                    'detected_chapter': detected_chapter,
                    'matches': detected_chapter == chapter_key,
                    'chapter_key': chapter_key,
                    'url': submission['url']
                })
        
        debug_info.append(user_debug)
    
    return render_template('debug.html', debug_info=debug_info)

@app.route('/api/refresh-cache', methods=['POST'])
def refresh_cache():
    cache['submissions'] = None
    cache['last_updated'] = 0
    submissions = fetch_all_submissions()
    return jsonify({'success': True, 'message': 'Cache refreshed'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
