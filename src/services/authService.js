import axios from 'axios';

const API_URL = 'http://localhost:8000/api/auth';

class AuthService {
    async register(username, email, password) {
        try {
            const response = await axios.post(`${API_URL}/register`, {
                username,
                email,
                password
            }, {
                withCredentials: true
            });
            return response.data;
        } catch (error) {
            throw error.response?.data || { detail: '注册失败' };
        }
    }

    async login(username, password) {
        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            console.log('正在发送登录请求...');
            const response = await axios.post(`${API_URL}/token`, formData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                withCredentials: true
            });

            console.log('登录响应:', response.data);

            if (response.data.access_token) {
                // 先保存token
                localStorage.setItem('user', JSON.stringify(response.data));
                
                try {
                    console.log('正在获取用户信息...');
                    const userInfo = await this.getCurrentUserInfo();
                    console.log('获取到的用户信息:', userInfo);
                    
                    // 更新用户信息
                    const userData = {
                        ...response.data,
                        ...userInfo
                    };
                    localStorage.setItem('user', JSON.stringify(userData));
                    return userData;
                } catch (userInfoError) {
                    console.error('获取用户信息失败:', userInfoError);
                    // 如果获取用户信息失败，仍然返回token信息
                    return response.data;
                }
            }
            return response.data;
        } catch (error) {
            console.error('登录失败，详细错误:', error);
            console.error('错误响应:', error.response?.data);
            throw error.response?.data || { detail: '登录失败' };
        }
    }

    logout() {
        localStorage.removeItem('user');
    }

    getCurrentUser() {
        return JSON.parse(localStorage.getItem('user'));
    }

    async getCurrentUserInfo() {
        try {
            const user = this.getCurrentUser();
            if (!user) {
                throw new Error('未登录');
            }

            const response = await axios.get('http://localhost:8000/api/users/me', {
                withCredentials: true
            });
            return response.data;
        } catch (error) {
            console.error('获取用户信息失败:', error);
            throw error.response?.data || { detail: '获取用户信息失败' };
        }
    }
}

export default new AuthService(); 