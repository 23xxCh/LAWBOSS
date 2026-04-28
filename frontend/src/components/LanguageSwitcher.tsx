import { useTranslation } from 'react-i18next';
import { Dropdown } from 'antd';

const LANGUAGES = [
  { code: 'zh', label: '中文', flag: '🇨🇳' },
  { code: 'en', label: 'English', flag: '🇺🇸' },
  { code: 'th', label: 'ไทย', flag: '🇹🇭' },
];

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const current = LANGUAGES.find((l) => l.code === i18n.language) || LANGUAGES[0];

  const changeLanguage = (code: string) => {
    i18n.changeLanguage(code);
    localStorage.setItem('locale', code);
  };

  return (
    <Dropdown
      menu={{
        items: LANGUAGES.map((lang) => ({
          key: lang.code,
          label: `${lang.flag} ${lang.label}`,
          onClick: () => changeLanguage(lang.code),
        })),
        selectedKeys: [i18n.language],
      }}
      trigger={['click']}
    >
      <span style={{ cursor: 'pointer', fontSize: 16 }}>
        {current.flag} {current.label}
      </span>
    </Dropdown>
  );
}
