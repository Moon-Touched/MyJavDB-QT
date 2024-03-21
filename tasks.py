from pydantic import BaseModel
import requests, time, re, os, asyncio
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal
from pikpakapi import PikPakApi
from settings import PIKPAK_Setting


class Movie(BaseModel):
    code: str = ""
    title: str = ""
    actors: list[str] = []
    tags: list[str] = []
    uncensored: bool = False
    magnet: str = ""
    url: str = ""
    local_existance: bool = False


class Actor(BaseModel):
    name: str = ""
    second_name: str = ""
    url: str = ""
    uncensored: bool = False
    movie_urls: list[str] = []
    total_movies: int = -1


class BaseTask(QThread):
    finished_signal = pyqtSignal()
    log_signal = pyqtSignal(str)

    def __init__(self, db) -> None:
        super().__init__()
        with open("cookie.txt", "r", encoding="utf-8") as file:
            cookie = file.read()

        self.headers: dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
            "Cookie": cookie,
        }

        self.db = db

    def get_soup(self, url: str):
        with requests.Session() as session:
            response = session.get(url, headers=self.headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
        return soup


class OneMovieInfoTask(BaseTask):
    def __init__(self, db, movie_url: str, uncensored: bool, time_interval: float) -> None:
        super().__init__(db)
        self.movie_url = movie_url
        self.uncensored = uncensored
        self.time_interval = time_interval

    def run(self):
        movie_collection = self.db["movie"]
        exist_movie = movie_collection.find_one({"url": self.movie_url})
        if exist_movie:
            self.log_signal.emit("数据库中已有该电影。")
            self.finished_signal.emit()
            return

        self.log_signal.emit(f"开始抓取 {self.movie_url}")
        movie_soup = self.get_soup(self.movie_url)

        try:
            info_panel = movie_soup.find("nav", class_="panel movie-panel-info")
        except AttributeError:  # movie_soup返回None
            self.log_signal.emit(f"{self.movie_url} 未获取影片信息，可能是FC2页面登陆失败，请检查cookie是否过期")
            return

        movie_info = Movie()
        movie_info.uncensored = self.uncensored
        movie_info.url = self.movie_url
        # 开始抓取
        cracked = False
        blocks = info_panel.find_all("div", class_="panel-block", recursive=False)
        for block in blocks:
            if block.find("strong"):
                block_name = block.find("strong").text

            if block_name == "番號:":
                span = block.find("span")
                if span.find("a"):
                    first_code = span.find("a").text
                else:
                    first_code = span.text
                last_code = block.find("span").text.split(first_code)[1]
                movie_info.code = f"{first_code}{last_code}"

            elif block_name == "類別:":
                tags = block.find_all("a")
                for tag in tags:
                    movie_info.tags.append(tag.text)
                    if tag == "無碼破解":
                        cracked = True

            elif block_name == "演員:":
                if not block.find("div", class_="control ranking-tags"):
                    actors = block.find_all("a")
                    for actor in actors:
                        movie_info.actors.append(actor.text)

        # 获取标题（网页上默认显示的）
        movie_info.title = movie_soup.find("strong", class_="current-title").text

        # 获取磁链，磁链只保存一个优先选无码破解，字幕次之，都没有选第一个
        magnet_list = movie_soup.find_all("div", class_="magnet-name column is-four-fifths")
        if len(magnet_list) > 0:
            if cracked:
                for magnet in magnet_list:
                    magnet_name = magnet.find("span", class_="name").text
                    if re.search("无码", magnet_name):
                        movie_info.magnet = magnet.find("a")["href"]

            # 没有无码破解
            if movie_info.magnet == "":
                for magnet in magnet_list:
                    magnet_tags = magnet.find_all("span", class_="tag is-primary is-small is-light")
                    for magnet_tag in magnet_tags:
                        if re.search("字幕", magnet_tag.text):
                            movie_info.magnet = magnet.find("a")["href"]
                            break

            # 没有无码也没有字幕，找到第一个
            if movie_info.magnet == "":
                movie_info.magnet = magnet_list[0].find("a")["href"]

        res = movie_collection.insert_one(movie_info.model_dump())
        self.log_signal.emit(f"{movie_info.code}已存储")
        time.sleep(self.time_interval)
        self.finished_signal.emit()
        return


class OneActorInfoTask(BaseTask):
    def __init__(self, db, actor_url: str, update: bool, time_interval: float) -> None:
        super().__init__(db)
        self.actor_url = actor_url
        self.update = update
        self.time_interval = time_interval

    def run(self):
        actor_collection = self.db["actor"]
        if not self.update:
            exist_actor = actor_collection.find_one({"url": self.actor_url})
            if exist_actor:
                self.log_signal.emit("数据库中已有该演员。")
                self.finished_signal.emit()
                return

        base_url = "https://javdb.com"

        soup = self.get_soup(self.actor_url)

        # 获取名字，是否无码
        actor_name_text = soup.find("span", class_="actor-section-name").text.split(", ")
        actor_name = actor_name_text[0]
        second_name = actor_name_text[0]
        if actor_name_text[-1][-4:] == "(無碼)":
            uncensored = True
            second_name = actor_name[:-4]
        else:
            uncensored = False

        # 有些有多个名字，在获取一个备用
        if len(actor_name_text) > 1:
            second_name = actor_name_text[1]

        # 获取一共有多少部
        total_movies = 0
        url_list = []
        i = 1
        while True:
            page_url = f"{self.actor_url}?page={i}"
            with requests.Session() as session:
                response = session.get(page_url, headers=self.headers)
            soup = BeautifulSoup(response.text, "html.parser")
            if soup.find("div", class_="empty-message"):
                break

            # 获取影片列表中的所有条目
            movie_container = soup.find("div", class_="movie-list h cols-4 vcols-8")
            if not movie_container:
                movie_container = soup.find("div", class_="movie-list h cols-4 vcols-5")

            movie_list = movie_container.find_all("div", class_="item", recursive=False)
            n = len(movie_list)
            total_movies = total_movies + n
            for movie in movie_list:
                movie_url = base_url + movie.find("a")["href"]
                url_list.append(movie_url)
            i = i + 1
            time.sleep(self.time_interval)

        actor_info = Actor()
        actor_info.name = actor_name
        actor_info.second_name = second_name
        actor_info.url = self.actor_url
        actor_info.movie_urls = url_list
        actor_info.total_movies = total_movies
        actor_info.uncensored = uncensored
        if self.update:
            actor_collection.update_one({"url": self.actor_url}, {"$set": actor_info.model_dump()})
        else:
            actor_collection.insert_one(actor_info.model_dump())
        self.log_signal.emit(f"{actor_name}已存储")
        self.finished_signal.emit()
        return


class FavouriteActorTask(BaseTask):
    def __init__(self, db, time_interval: float) -> None:
        super().__init__(db)
        self.time_interval = time_interval
        self.actor_urls = []
        self.cur_index = 0

    def run(self):
        soup = self.get_soup("https://javdb.com/users/collection_actors")

        # 获取收藏演员信息框
        actor_boxes = soup.find_all("div", class_="box actor-box")
        for box in actor_boxes:
            actor_sub_url = box.find("a")["href"]
            self.actor_urls.append(f"https://javdb.com{actor_sub_url}")

        self.run_next()

    def run_next(self):
        if self.cur_index < len(self.actor_urls):
            url = self.actor_urls[self.cur_index]
            self.cur_index += 1
            self.sub_task = OneActorInfoTask(db=self.db, actor_url=url, update=False, time_interval=self.time_interval)
            self.sub_task.finished_signal.connect(self.run_next)
            self.sub_task.log_signal.connect(self.forward_log)
            self.sub_task.start()
        else:
            self.log_signal.emit("全部抓取完成")
            self.finished_signal.emit()

    def forward_log(self, message):
        self.log_signal.emit(message)


class OneActorAllMovieTask(BaseTask):
    def __init__(self, db, actor_name: str, time_interval: float) -> None:
        super().__init__(db)
        self.actor_name = actor_name
        self.time_interval = time_interval
        self.movie_urls = []
        self.cur_index = 0

        self.uncensored = False

    def run(self):
        actor_collection = self.db["actor"]
        actor = actor_collection.find_one({"name": self.actor_name})
        movie_collection = self.db["movie"]
        count = movie_collection.count_documents({"actors": actor["second_name"], "uncensored": actor["uncensored"]})
        self.log_signal.emit(f"{self.actor_name}共有{actor['total_movies']}部，数据库中已有{count}部")
        if count < actor["total_movies"]:
            self.uncensored = actor["uncensored"]
            self.movie_urls = actor["movie_urls"]

            self.run_next()
        else:
            self.finished_signal.emit()

    def run_next(self):
        if self.cur_index < len(self.movie_urls):
            url = self.movie_urls[self.cur_index]
            self.cur_index += 1
            self.sub_task = OneMovieInfoTask(db=self.db, movie_url=url, uncensored=self.uncensored, time_interval=self.time_interval)
            self.sub_task.finished_signal.connect(self.run_next)
            self.sub_task.log_signal.connect(self.forward_log)
            self.sub_task.start()
        else:
            self.log_signal.emit("全部抓取完成")
            self.finished_signal.emit()

    def forward_log(self, message):
        self.log_signal.emit(message)


class MagnetTask(BaseTask):
    def __init__(self, db, actor_name: str, code: str, save_to_pikpak: bool, time_interval: float) -> None:
        super().__init__(db)
        self.actor_name = actor_name
        self.code = code
        self.time_interval = time_interval
        self.save_to_pikpak = save_to_pikpak

    def run(self):
        asyncio.run(self.main())

    async def main(self):
        if self.save_to_pikpak:
            client = PikPakApi(username=PIKPAK_Setting["username"], password=PIKPAK_Setting["password"])
            await client.login()
        actor_collection = self.db["actor"]
        actor = actor_collection.find_one({"name": self.actor_name})
        uncensored = actor["uncensored"]

        query = {
            "actors": actor["second_name"],
            "uncensored": uncensored,
        }
        if self.code != "":
            query["code"] = self.code

        movie_collection = self.db["movie"].find(query)

        for m in movie_collection:
            if m["magnet"] != "":
                if self.save_to_pikpak and not m["local_existance"]:
                    res = await client.create_folder(m["code"])
                    id = res["file"]["id"]
                    print(m["magnet"])
                    res = await client.offline_download(m["magnet"], parent_id=id)
                self.log_signal.emit(m["magnet"])
        self.finished_signal.emit()


class MatchInfoTask(BaseTask):
    def __init__(self, db, capture_path: str, movie_path: str, time_interval: float) -> None:
        super().__init__(db)
        self.capture_path = capture_path
        self.movie_path = movie_path
        self.time_interval = time_interval

    def run(self):
        movie_collection = self.db["movie"]
        files = self.get_file_list(self.capture_path)
        for file in files:
            file_name = file.split("\\")[-1]
            code, _, ext = file_name.rpartition(".")
            movie_info = movie_collection.find_one({"code": code})
            if movie_info == None:
                self.log_signal.emit(f"数据库中没有{movie_info['code']}相应数据")
            res = movie_collection.update_one({"code": code}, {"$set": {"local_existance": True}})
            ###到此信息获取完成，开始准备路径和重命名
            title = movie_info["title"]
            for i in range(len(title) - 1):
                if title[i] == ":" and i > 2:
                    a, _, b = title.rpartition(":")
                    title = f"{a}{b}"
            target_folder = os.path.join(self.movie_path, "capture done", f"{code}")
            if len(target_folder) > 80:
                target_folder = target_folder[:80]
            target_folder = target_folder.rstrip()
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)
            target_file = f"{target_folder}\\{file_name}"

            self.generate_nfo(movie_info, target_folder)
            self.get_one_movie_image(movie_url=movie_info["url"], movie_code=movie_info["code"], path=target_folder)

            os.rename(file, target_file)
            self.log_signal.emit(f"{file_name}整理完成")
        self.log_signal.emit("done！！！！！！！！")
        return

    def get_file_list(self, path: str, size_threshold: int = 524288000):
        files = []
        f = os.walk(path)
        root, movie_folders, file_names = next(f)
        for folder in movie_folders:
            large_files = []
            for root, dirs, file_names in os.walk(os.path.join(path, folder)):
                for file_name in file_names:
                    file_path = os.path.join(root, file_name)
                    if os.path.getsize(file_path) > size_threshold:
                        large_files.append({"file_path": file_path, "file_name": file_name})

            if len(large_files) == 1:
                name, _, ext = large_files[0]["file_name"].rpartition(".")
                new_name = f"{folder}.{ext}"
                new_path = os.path.join(path, folder, new_name)
                os.renames(large_files[0]["file_path"], new_path)
                files.append(new_path)
            elif large_files == []:
                continue
            else:
                self.log_signal.emit(f"{large_files[0]['file_path']}有多个大文件")
        return files

    def generate_nfo(self, movie_info: dict, path: str):
        nfo_content = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n<movie>\n'
        nfo_content += f"<title>{movie_info['code']}{movie_info['title']}</title>\n"
        for tag in movie_info["tags"]:
            nfo_content += f"<genre>{tag}</genre>\n"

        for tag in movie_info["tags"]:
            nfo_content += f"<tag>{tag}</tag>\n"

        for actor in movie_info["actors"]:
            nfo_content += "<actor>\n"
            nfo_content += f"<name>{actor}</name>\n"
            nfo_content += "</actor>\n"

        nfo_content += "</movie>\n"

        with open(f"{path}\\{movie_info['code']}.nfo", "w", encoding="utf-8") as file:
            file.write(nfo_content)
        return

    def get_one_movie_image(self, movie_url: str, movie_code: str, path: str):
        movie_soup = self.get_soup(movie_url)
        try:
            cover_url = movie_soup.find("img", class_="video-cover")["src"]
        except AttributeError:
            print("未获取影片信息，可能是FC2页面登陆失败，请检查cookie是否过期")
            return
        with requests.Session() as session:
            response = session.get(cover_url, headers=self.headers)

        with open(f"{path}\\{movie_code}-fanart.jpg", "wb") as file:
            file.write(response.content)
        with open(f"{path}\\{movie_code}-cover.jpg", "wb") as file:
            file.write(response.content)

        time.sleep(self.time_interval)
        return
