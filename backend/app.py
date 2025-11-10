from flask import Flask, render_template, jsonify, request
from github import Github, GithubException
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import re
import time
from supabase import create_client, Client

# 로컬 개발 환경 지원
if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__)

# GitHub 토큰 설정
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or os.getenv('GITHUB_TOKEN_BACKUP')

print(f"\n{'='*60}")
print("[INIT] GitHub 토큰 확인")
print(f"  토큰: {GITHUB_TOKEN[:20] if GITHUB_TOKEN else 'None'}...")

if GITHUB_TOKEN:
    try:
        g = Github(GITHUB_TOKEN)
        g.get_user().login
        print(f"  ✓ GitHub 연결 성공")
    except Exception as e:
        print(f"  ✗ GitHub 연결 실패: {str(e)}")
        g = None
else:
    g = None
    print(f"  [WARNING] GitHub API 사용 불가")
print(f"{'='*60}\n")

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
    "haeyin-lee": "이혜인",
    "jooyoung-lee": "이주영",
    "youlim-hong": "홍유림"
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
    "haeyin-lee",
    "jooyoung-lee",
    "youlim-hong",
]

STUDY_CONFIG = {
    "org_name": "oracleaistudy",
    "book_name": "혼자 공부하는 머신러닝 딥러닝",
    "part1_current_chapter": "6",
    "part2_current_chapter": "1-2",
}

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
    
    # 전체 진행률 계산
    total_completed = sum(data['total_completed'] for data in submissions.values())
    total_possible = members_count * 10
    avg_progress = round((total_completed / total_possible) * 100) if total_possible > 0 else 0
    
    # TOP 3 완료자
    top_users = sorted(
        submissions.items(),
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
    
    # 퀴즈 TOP 3
    quiz_top = []
    if supabase:
        try:
            response = supabase.table('quiz_completions').select('*').execute()
            user_counts = {}
            for record in response.data:
                user_name = record['user_name']
                user_counts[user_name] = user_counts.get(user_name, 0) + 1
            
            quiz_top = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:3]
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
                         top_users=top_users,
                         part1_avg=part1_avg,
                         part2_avg=part2_avg,
                         chapter_stats=chapter_stats,
                         part1_submissions=part1_submissions,  # 추가
                         part2_submissions=part2_submissions,  # 추가
                         quiz_top=quiz_top,
                         recent_papers=recent_papers,
                         part1_current=STUDY_CONFIG.get('part1_current_chapter', '6'),
                         part2_current=STUDY_CONFIG.get('part2_current_chapter', '1-2'))

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

if __name__ == '__main__':
    print("\n=== 등록된 라우트 ===")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    print("=" * 40 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
