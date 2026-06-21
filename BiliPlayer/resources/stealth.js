(() => {
    'use strict';

    // ==============================================
    // 1. 隐藏 webdriver 标记
    // ==============================================
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
    });

    // ==============================================
    // 2. 伪造 chrome 对象（B站关键检测点）
    // ==============================================
    if (!window.chrome) {
        window.chrome = {
            runtime: {},
            loadTimes: function () { },
            csi: function () { },
            app: {},
        };
    }
    // 确保 chrome.runtime 存在
    if (!window.chrome.runtime) {
        window.chrome.runtime = {};
    }

    // ==============================================
    // 3. 伪造 plugins（模拟真实Chrome）
    // ==============================================
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const arr = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
            ];
            arr.item = (i) => arr[i] || null;
            arr.namedItem = (name) => arr.find(p => p.name === name) || null;
            arr.refresh = () => { };
            Object.setPrototypeOf(arr, PluginArray.prototype);
            return arr;
        },
    });

    // ==============================================
    // 4. 伪造 mimeTypes
    // ==============================================
    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => {
            const arr = [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
            ];
            arr.item = (i) => arr[i] || null;
            arr.namedItem = (name) => arr.find(m => m.type === name) || null;
            Object.setPrototypeOf(arr, MimeTypeArray.prototype);
            return arr;
        },
    });

    // ==============================================
    // 5. 语言设置
    // ==============================================
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en-US', 'en'],
    });
    Object.defineProperty(navigator, 'language', {
        get: () => 'zh-CN',
    });

    // ==============================================
    // 6. 硬件信息
    // ==============================================
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
    });
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8,
    });
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32',
    });

    // ==============================================
    // 7. 权限API（避免异常行为暴露自动化）
    // ==============================================
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = function (parameters) {
        if (parameters.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission, onchange: null });
        }
        return originalQuery.call(this, parameters);
    };

    // ==============================================
    // 8. 删除 CDP 运行时检测属性
    // ==============================================
    const cdcKeys = [
        'cdc_adoQpoasnfa76pfcZLmcfl_Array',
        'cdc_adoQpoasnfa76pfcZLmcfl_Object',
        'cdc_adoQpoasnfa76pfcZLmcfl_Promise',
        'cdc_adoQpoasnfa76pfcZLmcfl_Proxy',
        'cdc_adoQpoasnfa76pfcZLmcfl_Symbol',
        'cdc_adoQpoasnfa76pfcZLmcfl_JSON',
    ];
    for (const key of cdcKeys) {
        delete window[key];
    }

    // ==============================================
    // 9. 伪造 connection.rtt
    // ==============================================
    if (navigator.connection) {
        Object.defineProperty(navigator.connection, 'rtt', {
            get: () => 50,
        });
    }

    // ==============================================
    // 10. 阻止 iframe 中自动化特征检测
    // ==============================================
    const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
    if (originalContentWindow) {
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function () {
                const win = originalContentWindow.get.call(this);
                if (win) {
                    try {
                        Object.defineProperty(win.navigator, 'webdriver', {
                            get: () => false,
                        });
                    } catch (e) { }
                }
                return win;
            },
        });
    }

    console.log('✅ Stealth 反检测脚本已注入');
})();
