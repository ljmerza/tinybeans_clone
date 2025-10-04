/**
 * Language Switcher Component
 * 
 * Allows users to change their preferred language.
 * Updates both the UI immediately and saves preference to backend.
 */
import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/features/auth/api/modernAuthClient';

type Language = 'en' | 'es';

const languages: { code: Language; label: string; flag: string }[] = [
  { code: 'en', label: 'English', flag: '🇺🇸' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
];

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const [saving, setSaving] = useState(false);
  const currentLanguage = i18n.language as Language;

  const handleLanguageChange = async (lang: Language) => {
    if (lang === currentLanguage) return;

    try {
      // Change language immediately for instant UI update
      await i18n.changeLanguage(lang);
      
      // Save preference to backend (if user is logged in)
      setSaving(true);
      try {
        await apiClient.patch('/users/me/', { language: lang });
      } catch (error) {
        console.error('Failed to save language preference:', error);
        // UI already updated, so not critical if backend save fails
      } finally {
        setSaving(false);
      }
    } catch (error) {
      console.error('Failed to change language:', error);
    }
  };

  return (
    <div className="flex gap-2 items-center">
      {languages.map((lang) => (
        <Button
          key={lang.code}
          variant={currentLanguage === lang.code ? 'default' : 'outline'}
          size="sm"
          onClick={() => handleLanguageChange(lang.code)}
          disabled={saving}
          className="flex items-center gap-2"
        >
          <span>{lang.flag}</span>
          <span>{lang.label}</span>
        </Button>
      ))}
    </div>
  );
}

/**
 * Compact language switcher for navigation bars
 */
export function LanguageSwitcherCompact() {
  const { i18n } = useTranslation();
  const [saving, setSaving] = useState(false);
  const currentLanguage = i18n.language as Language;

  const handleLanguageChange = async (lang: Language) => {
    if (lang === currentLanguage) return;

    try {
      await i18n.changeLanguage(lang);
      
      setSaving(true);
      try {
        await apiClient.patch('/users/me/', { language: lang });
      } catch (error) {
        console.error('Failed to save language preference:', error);
      } finally {
        setSaving(false);
      }
    } catch (error) {
      console.error('Failed to change language:', error);
    }
  };

  return (
    <select
      value={currentLanguage}
      onChange={(e) => handleLanguageChange(e.target.value as Language)}
      disabled={saving}
      className="px-2 py-1 text-sm border rounded"
    >
      {languages.map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.flag} {lang.label}
        </option>
      ))}
    </select>
  );
}
