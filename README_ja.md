# JAV Lib Manager 🎀

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-Latest-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

[English](README.md) | [简体中文](README_zh.md) | [日本語](#日本語)

*個人ビデオコレクション管理のためのモダンなデスクトップアプリケーション*

</div>

---

## 日本語

### 紹介

🎀 **JAV Lib Manager** は、個人ビデオコレクション管理のために設計された強力なデスクトップアプリケーションです。ローカルビデオファイルをインテリジェントに整理し、オンラインソースからメタデータを自動取得し、高度な検索・フィルタリング機能を提供します。

### 主な機能

- 🔍 **スマートスキャン** - ディレクトリを自動スキャンし、ファイル名から動画IDを抽出
- 🌐 **メタデータ取得** - JavDB からカバー、女優情報、タグを取得
- 🏷️ **多次元検索** - 動画ID、女優、タグ、スタジオで検索
- 📺 **モダンなUI** - PyQt6 ベースの美しいインターフェース、18種の Material Design テーマ
- 💾 **ローカルデータベース** - 大規模コレクションをサポートする SQLite
- 📷 **カバー キャッシュ** - カバー画像の自動ダウンロードとキャッシュ
- ⚡ **高性能** - マルチスレッド処理でスムーズな体験

### インターフェースプレビュー

```
┌─────────────────────────────────────────────────────┐
│  🎀 JAV Lib Manager                                    │
├─────────────────────────────────────────────────────┤
│  [スキャン] [更新] [統計] [ログ] [設定]               │
│  検索: [________________] [フィルター]                  │
├──────────────────────┬──────────────────────────────┤
│  ┌────┐ ┌────┐      │ カバー大図                    │
│  │封面│ │封面│      │ ┌─────────────────────────┐  │
│  │    │ │    │      │ │                         │  │
│  └────┘ └────┘      │ │   [高画質カバー]         │  │
│  ┌────┐ ┌────┐      │ │                         │  │
│  │封面│ │封面│      │ └─────────────────────────┘  │
│  │    │ │    │      │ タイトル: 動画タイトル      │
│  └────┘ └────┘      │ 女優: [女優1, 女優2]        │
│  ... その他の動画   │ タグ: [タグ1, タグ2, タグ3]  │
│                     │ スタジオ: スタジオ名        │
│                     │ ファイル: /path/to/video.mp4 │
└──────────────────────┴──────────────────────────────┘
```

### 動作環境

- **Python**: 3.9 以降 — [ダウンロード](https://www.python.org/downloads/)（インストール時に "Add Python to PATH" にチェックを入れてください）
- **オペレーティングシステム**: Windows 10/11
- **ディスク容量**: 依存関係のため 500MB 以上
- **ネットワーク**: メタデータ取得に必要

### インストール

#### 方法1: Gitを使用（推奨）

```bash
# 1. Pythonバージョンを確認（3.9以降必須）
python --version

# 2. リポジトリをクローン
git clone https://github.com/ShadyDon-EdoTensei/jav-lib-manager.git
cd jav-lib-manager

# 3. 仮想環境を作成（推奨）
python -m venv venv
venv\Scripts\activate

# 4. Python依存関係をインストール
pip install -r requirements.txt

# 5. Playwrightブラウザエンジンをインストール（約300MB、初回のみ）
playwright install chromium

# 6. アプリケーションを起動
python run_app.py
```

#### 方法2: ZIPをダウンロード（Git不要）

1. [リリース](https://github.com/ShadyDon-EdoTensei/jav-lib-manager/releases)から最新版をダウンロード
2. 任意のフォルダに解凍（例：`C:\jav-lib-manager\`）
3. そのフォルダで**コマンドプロンプト**または**PowerShell**を開く
4. 以下のコマンドを実行：
```bash
python --version          # Python 3.9以降を確認
pip install -r requirements.txt
playwright install chromium
python run_app.py
```

> **ヒント:** `python` コマンドが認識されない場合は、Pythonをインストールし、"Add Python to PATH"にチェックを入れてください。

### 使用ガイド

#### 初回使用

1. **アプリケーションを起動**
   ```bash
   python run_app.py
   ```

2. **ビデオディレクトリをスキャン**
   - ツールバーの **"スキャン"** ボタンをクリック
   - ビデオファイルが含まれるディレクトリを選択
   - スキャン完了まで待つ
   - 検出された動画数を確認

3. **メタデータを取得**
   - メタデータを自動取得するために **"はい"** を選択
   - 処理完了まで待つ
   - 動画がカバー付きでメイン画面に表示されます

#### 検索とフィルタ

- **キーワード検索**: 検索ボックスに動画ID、タイトル、女優名を入力
- **女優フィルタ**: ドロップダウンから女優を選択
- **タグフィルタ**: ドロップダウンからタグを選択
- **スタジオフィルタ**: ドロップダウンからスタジオを選択

#### 動画詳細を表示

任意の動画カードをクリックして表示：
- 高解像度カバー画像（クリックでフルサイズ表示）
- 完全な女優リスト
- タグカテゴリー
- ファイル情報（パス、サイズ、日付）

#### テーマを変更

1. **"設定"** ボタンをクリック
2. **"外観設定"** タブに移動
3. 好みのテーマを選択（18種類のオプション）
4. **"保存"** をクリック

### 設定

設定ファイル: `~/.javlibrary/config.json`

```json
{
  "database_path": "data/library.db",
  "covers_dir": "data/images/covers",
  "theme": "dark_amber",
  "window_width": 1600,
  "window_height": 900,
  "scraper_delay": 2,
  "scraper_timeout": 30
}
```

### プロジェクト構造

```
jav-lib-manager/
├── README.md                 # 英語ドキュメント
├── README_zh.md              # 中国語ドキュメント
├── README_ja.md              # 日本語ドキュメント
├── LICENSE                   # MIT ライセンス
├── .gitignore                # Git 無視ルール
├── CONTRIBUTING.md           # コントリビューションガイドライン
├── CODE_OF_CONDUCT.md        # コミュニティガイドライン
├── CHANGELOG.md              # バージョン履歴
├── requirements.txt          # Python 依存関係
├── run_app.py                # アプリケーションエントリポイント
├── src/                      # ソースコード
│   ├── __init__.py
│   ├── main.py
│   ├── gui/                  # PyQt6 UI
│   │   ├── main_window.py
│   │   ├── themes/
│   │   └── dialogs/
│   ├── core/                 # コアロジック
│   │   ├── models.py
│   │   ├── parser.py
│   │   ├── scanner.py
│   │   ├── scraper.py
│   │   ├── javdb_scraper.py
│   │   ├── database.py
│   │   └── cover_downloader.py
│   └── utils/                # ユーティリティ
│       ├── config.py
│       └── logger.py
├── docs/                     # 追加ドキュメント
├── tests/                    # テストファイル
└── data/                     # ランタイムデータ（git無視）
    ├── library.db
    └── images/
```

### 技術スタック

| コンポーネント | 技術 |
|------------|------|
| **GUI フレームワーク** | PyQt6 |
| **テーマエンジン** | qt-material |
| **データベース** | SQLite |
| **ウェブスクレイピング** | Playwright + requests + lxml |
| **画像処理** | Pillow |
| **アイコン** | qtawesome (FontAwesome 5) |

### 対応動画フォーマット

MP4、MKV、AVI、WMV、MOV、FLV、M4V、TS、WebM

### データソース

- **JavDB**（デフォルト、Playwright アンチ検出付き）
- 将来的なリリースでより多くのソースを計画中

### よくある質問

**Q: データはサーバーにアップロードされますか？**

A: いいえ。すべてのデータはローカルコンピューターに保存されます。データベースは `~/.javlibrary/data/library.db` にあります。

**Q: Linux/Mac で使用できますか？**

A: 現在、公式には Windows のみサポートされています。Linux/Mac サポートは将来のリリースで計画されています。

**Q: データをバックアップするには？**

A: `~/.javlibrary/` ディレクトリ全体をバックアップしてください。

**Q: メタデータ取得が失敗した場合は？**

A:
1. インターネット接続を確認
2. 設定でスクレイパー遅延を増やしてみる
3. ログファイル `~/.javlibrary/logs/javlibrary.log` を確認

**Q: カスタムデータソースを追加できますか？**

A: この機能は v2.0.0 で計画されています。お楽しみに！

### ロードマップ

- [ ] 動画プレイヤー統合
- [ ] Linux と Mac サポート
- [ ] カスタムメタデータソース
- [ ] 一括ファイル名変更
- [ ] CSV/JSON へのエクスポート
- [ ] 高度な統計とレポート

### コントリビューション

コントリビューションを歓迎します！詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

### 行動規範

[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) を読んで、私たちのコミュニティ基準を理解してください。

### ライセンス

このプロジェクトは MIT ライセンスの下でライセンスされています - 詳細は [LICENSE](LICENSE) を参照してください

### 謝辞

- **PyQt6 チーム** - 素晴らしい GUI フレームワークに感謝
- **Playwright チーム** - 信頼できるブラウザ自動化に感謝
- **qt-material** - 美しい Material Design テーマに感謝
- **すべてのコントリビューター** - プロジェクトをより良くしてくれてありがとう！

### サポート

- 📧 メール: ShadyDon-EdoTensein@users.noreply.github.com
- 🐛 問題報告: [GitHub Issues](https://github.com/ShadyDon-EdoTensei/jav-lib-manager/issues)
- 💬 ディスカッション: [GitHub Discussions](https://github.com/ShadyDon-EdoTensei/jav-lib-manager/discussions)

---

<div align="center">

**⭐ このプロジェクトが役立つと思ったら、スターを検討してください！⭐**

❤️ と 🎀 で作られた JAV Lib Manager

</div>
