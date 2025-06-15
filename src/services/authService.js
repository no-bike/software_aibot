import axios from 'axios';

const API_URL = 'http://localhost:8000/api/auth';

class AuthService {
    async register(username, email, password) {
        try {
            const response = await axios.post(`${API_URL}/register`, {
                username,
                email,
                password
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

            const response = await axios.post(`${API_URL}/token`, formData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });

            if (response.data.access_token) {
                localStorage.setItem('user', JSON.stringify(response.data));
            }
            return response.data;
        } catch (error) {
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

            const response = await axios.get(`${API_URL}/users/me`, {
                headers: {
                    'Authorization': `Bearer ${user.access_token}`
                }
            });
            return response.data;
        } catch (error) {
            throw error.response?.data || { detail: '获取用户信息失败' };
        }
    }
}

export default new AuthService(); 