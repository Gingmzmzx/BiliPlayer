(async function () {
    'use strict';

    // 如果已登录，不需要运行
    if (document.cookie.includes('DedeUserID')) return;

    if (window.location.hostname === 'www.bilibili.com') {

        // ==============================================
        // 1. 禁止加载登录弹窗脚本
        // ==============================================
        const originAppendChild = Node.prototype.appendChild;
        Node.prototype.appendChild = function (childElement) {
            if (childElement.tagName === 'SCRIPT' && childElement.src.includes('miniLogin')) {
                return null;
            }
            return originAppendChild.call(this, childElement);
        };

        // ==============================================
        // 2. 等待播放器加载完成
        // ==============================================
        await new Promise(resolve => {
            const timer = setInterval(() => {
                if (window.player && window.player.getMediaInfo) {
                    clearInterval(timer);
                    resolve();
                }
            }, 1000);
        });

        // ==============================================
        // 3. 绕过自动暂停（修改播放时间）
        // ==============================================
        const originGetMediaInfo = window.player.getMediaInfo;
        window.player.getMediaInfo = function () {
            const info = originGetMediaInfo();
            info.absolutePlayTime = 0;
            return info;
        };

        // ==============================================
        // 4. 只允许手动暂停
        // ==============================================
        let isClickedRecently = false;
        document.body.addEventListener('click', () => {
            isClickedRecently = true;
            setTimeout(() => isClickedRecently = false, 500);
        });

        const originPause = window.player.pause;
        window.player.pause = function () {
            if (!isClickedRecently) return;
            return originPause.call(this);
        };

        // ==============================================
        // 5. 隐藏登录弹窗
        // ==============================================
        const style = document.createElement('style');
        style.textContent = `
      .bili-mini-mask, .bili-mini-register, .login-panel { display: none !important; }
    `;
        document.head.appendChild(style);

        // ==============================================
        // 6. 【新增】禁止自动连播下一个视频
        // ==============================================
        // 模拟点击.continuous-btn元素 $(".continuous-btn").click();
        const continuousBtn = document.querySelector('.continuous-btn');
        if (continuousBtn) {
            continuousBtn.click();
        }
        

        console.log("✅ 防暂停/防弹窗/防自动连播 已启动");
    }
})();

(function () {
    // 创建 script 标签
    var script = document.createElement('script');
    // 加载 jQuery 官方完整版（最新稳定版）
    script.src = 'https://code.jquery.com/jquery-3.7.1.min.js';
    // 加载完成后提示并输出版本
    script.onload = function () {
        console.log('✅ jQuery 加载成功！版本：' + jQuery.fn.jquery);
        
        var video = $('video');
        video.off('ended');
        video.on('ended', function () {
            biliMusic_on_ended();
        });
        video.on('timeupdate', function () {
            biliMusic_on_timeupdate(this.currentTime, this.duration);
        });
    };
    // 插入到页面
    document.head.appendChild(script);
})();