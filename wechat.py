import logging
from datetime import datetime

from pywinauto.findwindows import find_elements
from pyzbar import pyzbar

from app import UiaApp, AppConfig, AppUser, MessageType

import psutil

def find_process_id_by_name(process_name):
    # 获取所有运行中的进程
    for proc in psutil.process_iter(attrs=['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc.info['pid']
    return None


class WeChat(UiaApp):
    def __init__(self, handle: int, process: int = None, status: int = None, user=None):
        super().__init__(handle, process, status, user)
        self.version = "3.5.0.46"

    @staticmethod
    def config():
        return AppConfig(
            app_name="wechat",
            login_class_name="WeChatLoginWndForPC",
            main_class_name="WeChatMainWndForPC",
            process_name="WeChat.exe",
            mutex_names=[r"\_WeChat_App_Instance_Identity_Mutex_Name"],
            registry_path=r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\WeChat",
            registry_key="DisplayIcon")

    def find_userinfo(self):
        wechat_app = self.connect(self.handle)
        wechat_window = wechat_app.window(class_name="WeChatMainWndForPC")
        # Click avatar button and show user profile card
        chats_button = wechat_window.child_window(control_type='Button', title='聊天')
        avatar_button = chats_button.parent().children()[0]
        avatar_button.click_input()
        # Find account
        account_label = wechat_window.child_window(control_type='Text', title='微信号：')
        account_box = account_label.parent()
        account = account_box.children()[1].window_text()
        if account is None:
            return None
        # Find nickname
        userinfo_box = account_box.parent()
        nickname_box = userinfo_box.children()[0]
        nickname = nickname_box.children()[0].window_text()
        # Hide user profile card
        avatar_button.click_input()
        return AppUser(account=account, nickname=nickname)

    def login(self, data=None):
        logging.debug('Login, handle: %d', self.handle)
        wechat_app = self.connect(self.handle)
        wechat_window = wechat_app.window(class_name="WeChatLoginWndForPC")
        try:
            # I'm not quite sure about the difference between "账号" and "帐号"
            switch_account_button = wechat_window.child_window(control_type='Button', title_re='切换账号|切换帐号')
            if switch_account_button and switch_account_button.exists():
                switch_account_button.click_input()
        except:
            logging.debug("Switch button cannot be found, whatever")
        snapshot = self.snapshot(self.handle)
        decoded = pyzbar.decode(snapshot)
        if decoded and decoded[0]:
            return {'qrcode': decoded[0].data.decode('utf-8')}
        raise Exception("Failed to obtain QR code")

    def logout(self, data=None):
        logging.debug('Logout, handle: %d', self.handle)
        self.close_handle(self.handle)

    def send_private_messages(self, data):
        logging.debug('Send private messages, handle: %d, data: %s', self.handle, data)
        # Validate data before sending messages
        target, messages, file_paths = self._check_messages(data)
        wechat_app = self.connect(self.handle)
        wechat_window = wechat_app.window(class_name="WeChatMainWndForPC")
        # Open contact manager
        contact_button = wechat_window.child_window(control_type='Button', title='通讯录')
        contact_button.click_input()
        contact_manager_button = wechat_window.child_window(control_type='Button', title='通讯录管理')
        contact_manager_button.click_input()
        contact_manager_elements = find_elements(process=self.process, title="通讯录管理")
        if not contact_manager_elements:
            raise Exception("Failed to open contact manager")
        contact_manager_handle = contact_manager_elements[0].handle
        contact_manager_app = self.connect(contact_manager_handle)
        contact_manager_window = contact_manager_app.window(class_name='ContactManagerWindow')
        # Search the friend
        search_edit = contact_manager_window.child_window(control_type='Edit', title='搜索')
        search_edit.click_input()
        search_edit.type_keys('^a')
        search_edit.type_keys(target, with_spaces=True, with_tabs=True, with_newlines=True)
        friend_button = contact_manager_window.child_window(control_type='Button', title=target)
        friend_button.click_input()
        send_button = contact_manager_window.child_window(control_type='Button', title='发消息')
        send_button.click_input()
        # Send messages
        self._send_messages(wechat_window, target, messages, file_paths)
        try:
            self.close_handle(contact_manager_handle)
        except:
            logging.debug("Failed to close windows, but ok")


    def send_url(self, data):
        """
        data['url']
        data['target']
        """
        from pywinauto.findwindows import find_elements
        logging.debug('Send url, handle: %d, data: %s', self.handle, data)
        wechat_app = self.connect(self.handle)
        wechat_window = wechat_app.window(class_name="WeChatMainWndForPC")
        view_button = wechat_window.child_window(control_type='Button', title='看一看')
        logging.debug(view_button)
        view_button.click_input()
        elements = find_elements(class_name='Chrome_WidgetWin_0')

        view_app = self.connect(elements[0].handle)
        view_window = view_app.window(class_name="Chrome_WidgetWin_0")
        table_elements = view_window.child_window(control_type='Tab')

        panes = table_elements.children()
        # 假设我们要找到并点击第二个窗格
        if len(panes) > 1:
            second_pane = panes[1]  # 第二个窗格的索引是1
            second_pane.click_input()     # 执行点击操作
        else:
            print("没有找到第二个窗格")

        search_edit = view_window.child_window(control_type='Edit', title='地址和搜索栏')
        search_edit.click_input()
        search_edit.type_keys(data['url'])
        search_edit.type_keys('{ENTER}')

        for r in data['target']:
            try:
                more_button = view_window.child_window(title='更多')
                more_button.click_input()

                view_window.child_window(title='转发给朋友').click_input()

                for i in range(3):
                    try:
                        # 获取 'SelectContactWnd' 窗口句柄
                        elements = find_elements(class_name='SelectContactWnd')
                        if not elements:
                            raise Exception('没有找到 SelectContactWnd 窗口')
                        break
                    except Exception as e:
                        logging.error(e)
                        continue

                # 进一步筛选窗口，确保找到正确的窗口
                select_window = None
                for elem in elements:
                    if elem.name == "":  # 根据窗口的其他属性进行筛选
                        select_window = self.connect(elem.handle).window(class_name="SelectContactWnd")
                        break

                if not select_window:
                    raise Exception('没有找到符合条件的 SelectContactWnd 窗口')

                search_edit = select_window.child_window(control_type='Edit', title='搜索')
                search_edit.click_input()
                search_edit.type_keys(r, with_spaces=True, with_tabs=True, with_newlines=True)
                search_edit.type_keys('{ENTER}')

                select_window.child_window(title='发送', control_type='Button').click_input()
            except Exception as e:
                logging.error(e)





    def send_group_messages(self, data):
        logging.debug('Send group messages, handle: %d, data: %s', self.handle, data)
        # Validate data before sending messages
        target, messages, file_paths = self._check_messages(data)
        wechat_app = self.connect(self.handle)
        wechat_window = wechat_app.window(class_name="WeChatMainWndForPC")
        # Open contact manager
        search_edit = wechat_window.child_window(control_type='Edit', title='搜索')
        search_edit.click_input()
        search_edit.type_keys('^a')
        search_edit.type_keys(target, with_spaces=True, with_tabs=True, with_newlines=True)
        self.wait(1)
        # Find group
        result_list = wechat_window.child_window(control_type='List', title='搜索结果')
        group_button = result_list.child_window(control_type='Button', title=target)
        group_button.click_input()
        # Send messages
        self._send_messages(wechat_window, target, messages, file_paths)

    def add_contacts(self, data):
        logging.debug('Add contacts, handle: %d, data: %s', self.handle, data)
        raise NotImplementedError

    def post_moments(self, data):
        logging.debug('Post moments, handle: %d, data: %s', self.handle, data)
        raise NotImplementedError

    def _check_messages(self, data):
        if not data or not data.get('target') or not data.get('messages'):
            raise Exception("Invalid data")
        target = data['target']
        messages = data['messages']
        for m in messages:
            if 'type' not in m or 'content' not in m:
                raise Exception("Invalid messages")
        dir_path = "{}\\{}\\{}".format(self.temps_path, self.app_id(), datetime.now().strftime('%Y%m%d'))
        file_types = [MessageType.IMAGE, MessageType.VIDEO, MessageType.FILE]
        file_urls = [message['content'] for message in messages if message['type'] in file_types]
        file_paths = self.download(file_urls, dir_path)
        return target, messages, file_paths

    def _send_messages(self, wechat_window, target, messages, file_paths):
        input_box = wechat_window.child_window(control_type='Edit', title_re=f'输入|{target}')
        input_box.type_keys('^a')
        for message in messages:
            type = message.get('type')
            content = message.get('content')
            if type == MessageType.TEXT:
                input_box.type_keys(content, with_spaces=True, with_tabs=True, with_newlines=True)
            elif type == MessageType.IMAGE or type == MessageType.VIDEO or type == MessageType.FILE:
                self.copy(file_paths[content])
                file_button = wechat_window.child_window(control_type='Button', title='发送文件')
                file_button.click_input()
                file_name_edit = wechat_window.child_window(control_type='Edit', title='文件名(N):')
                file_name_edit.type_keys('^a^v')
                file_name_edit.type_keys('{ENTER}')
            elif type == MessageType.MENTION:
                input_box.type_keys('@')
                input_box.type_keys(content, with_spaces=True, with_tabs=True, with_newlines=True)
                input_box.type_keys('{ENTER}')
            else:
                logging.error("Unsupported")
        input_box.type_keys('{ENTER}')


if __name__ == '__main__':

    # 查找微信的进程 ID
    wechat_pid = find_process_id_by_name("WeChat.exe")
    if wechat_pid:
        print(f"WeChat Process ID: {wechat_pid}")
    else:
        print("WeChat process not found.")

    elements = WeChat.find_elements(wechat_pid)
    first = elements[0]
    wechat = WeChat(first.handle, first.process_id, 0)
    # wechat.login()
    # wechat.logout()
    # wechat.send_private_messages({'target': '玲儿响当当', 'messages': [{'type': MessageType.TEXT, 'content': 'test'}]})
    wechat.send_url({'url':'https://mp.weixin.qq.com/s/4SfQ6NJHRNVuNGmWuWke7A', 'target': ['数字游民社区',
    'AIGC前沿资讯7群',
    '游戏玩家交流群']})
    # wechat.send_group_messages({'target': 'test', 'messages': [{'type': MessageType.TEXT, 'content': 'test'}])
    # wechat.add_contacts({'target': 'test'})
    # wechat.post_moments({'target': 'test'})