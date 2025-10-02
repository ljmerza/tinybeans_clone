import { Link } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import { authStore } from './modules/login/store'

function App() {
  const { accessToken } = useStore(authStore)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="container-page">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Link to="/" className="text-xl font-bold text-gray-900 hover:text-gray-700">
                Home
              </Link>
            </div>
            <nav className="flex items-center gap-4">
              {accessToken ? (
                <Link to="/logout" className="btn-ghost">
                  Logout
                </Link>
              ) : (
                <>
                  <Link to="/login" className="btn-ghost">
                    Login
                  </Link>
                  <Link to="/signup" className="btn-primary">
                    Sign up
                  </Link>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      <main className="container-page section-spacing">
        <div className="text-center">
          <h1 className="heading-1 mb-4">
            Welcome
          </h1>
          <p className="text-subtitle mb-8">
            {accessToken 
              ? 'You are signed in!' 
              : 'Get started by signing up or logging in to your account.'}
          </p>
        </div>
      </main>
    </div>
  )
}

export default App
