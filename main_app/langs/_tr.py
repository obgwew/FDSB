# -*- coding: utf-8 -*-
# main_app/langs/tr.py

TURKISH_DICT = {
    # ── Main Interface ────────────────────────────────────────
    'main_title':          (1001, 'FDSB'),
    'no_bots_hint':        (1002, 'Hiç bot bulunamadı. Yeni bir tane oluşturmak için "Yeni Bot"a tıklayın.'),
    'new_bot':             (1003, 'Yeni Bot'),
    'discord':             (1004, 'Discord'),
    'github':              (1005, 'GitHub'),

    # ── Create Bot Window ─────────────────────────────────────
    'name_label':          (1006, 'İsim'),
    'token_label':         (1007, 'Token'),
    'name_hint':           (1008, 'Bot adını girin'),
    'token_hint':          (1009, 'Bot tokenini girin'),
    'make':                (1010, 'Oluştur'),
    'image_label':         (1011, 'Resim'),
    'ok':                  (1012, 'Tamam'),
    'token_required':      (1013, 'Token gerekli'),
    'name_taken':          (1014, 'Bu isim zaten kullanılıyor\nBaşka bir isim seçin'),
    'token_invalid_format':(1015, 'Token formatı geçerli değil.'),

    # ── Bot Dashboard ─────────────────────────────────────────
    'state_server':        (1016, 'Sunucu durumu'),
    'online':              (1017, 'Çevrimiçi'),
    'offline':             (1018, 'Çevrimdışı'),
    'start':               (1019, 'Başlat'),
    'stop':                (1020, 'Durdur'),
    'starting':            (1021, 'Bağlanılıyor...'),
    'stopping':            (1022, 'Durduruluyor...'),
    'servers_count':       (1023, 'Sunucular'),
    'whats_new':           (1024, 'Yenilikler'),
    'no_updates':          (1025, 'Kullanılabilir güncelleme yok.'),
    'no_file':             (1026, 'Güncelleme dosyası bulunamadı.'),
    'read_error':          (1027, 'Dosya okunamadı.'),
    'invite_bot':          (1028, 'Botu davet et'),
    'back':                (1029, 'Geri'),
    'avatar_none':         (1030, 'Avatar yok'),

    # ── Navigation Tabs ───────────────────────────────────────
    'tab_main':            (1117, 'Ana Sayfa'),
    'tab_commands':        (1118, 'Komutlar'),
    'tab_variables':       (1119, 'Değişkenler'),
    'tab_settings':        (1120, 'Ayarlar'),
    'tab_wiki':            (1121, 'Wiki'),

    # ── Settings ──────────────────────────────────────────────
    'general_section':     (1031, 'Genel'),
    'design_section':      (1032, 'Tasarım'),
    'info_section':        (1033, 'Bilgi'),
    'name_project':        (1034, 'Proje adı'),
    'token_field':         (1035, 'Bot tokeni'),
    'bot_name_hint':       (1036, 'Bot adı'),
    'bot_token_hint':      (1037, 'Bot tokeni'),
    'save':                (1038, 'Kaydet'),
    'language':            (1039, 'Dil'),
    'wiki':                (1040, 'Wiki'),
    'link':                (1041, '(bağlantı)'),
    'restart_notice':      (1042, 'Yeniden başlatılıyor...'),
    'search_lang':         (1043, 'Dil ara...'),
    'select_language':     (1044, 'Dil seçin'),
    'selfbot_token_blocked': (1045, 'Güvenlik nedeniyle kullanıcı/selfbot tokenlerinin kullanımı kesinlikle yasaktır.'),
    'invalid_bot_token':   (1046, 'Bot tokeni geçersiz. Lütfen resmi bir Discord bot tokeni girin.'),

    # ── Export Data ───────────────────────────────────────────
    'export_section':      (1047, 'Verileri dışa aktar'),
    'export_desc':         (1048, 'Komutları ve değişkenleri ZIP dosyası olarak dışa aktarın'),
    'export_zip':          (1049, 'ZIP olarak dışa aktar'),
    'no_bot_selected':     (1050, 'Hiçbir bot seçilmedi!'),
    'folders_not_found':   (1051, 'Klasörler bulunamadı!'),
    'export_failed':       (1052, 'Dışa aktarma başarısız oldu!'),
    'export_success':      (1053, 'Başarıyla dışa aktarıldı!'),

    # ── Danger Zone / Delete ──────────────────────────────────
    'danger_zone':         (1054, 'Tehlikeli bölge'),
    'delete_bot_perm':     (1055, 'Bu botu kalıcı olarak sil'),
    'captcha_enter':       (1056, '3 haneyi girin'),
    'captcha_hint':        (1057, 'Yukarıda gösterilen 3 haneyi girin'),
    'confirm_delete':      (1058, 'Silmeyi onayla'),
    'captcha_wrong':       (1059, 'Yanlış kod — tekrar deneyin'),

    # ── Themes Names ──────────────────────────────────────────
    'system_wh':           (1060, 'Sistem (Açık)'),
    'system_da':           (1061, 'Sistem (Koyu)'),
    'blue_sky':            (1062, 'Mavi - Gökyüzü'),
    'yellow_bile':         (1063, 'Sarı - Altın'),
    'v2_dark':             (1064, 'Koyu Altın'),

    # ── commands_view ─────────────────────────────────────────
    'commands_slash':      (1065, '/ Komutları'),
    'info_command':        (1066, 'Komut bilgisi'),
    'command_editor':      (1067, 'Komut düzenleyici'),
    'total_lines':         (1068, 'Satırlar'),
    'total_text':          (1069, 'Karakterler'),
    'fdscript_hint':       (1070, '# FDScript kodunu buraya yazın...'),
    'prefix_label':        (1071, 'Önek'),
    'prefix_hint':         (1072, 'Örnek: !cmd'),
    'search':              (1073, 'Ara'),
    'commands':            (1074, 'Komutlar'),
    'no_cmds_hint':        (1075, 'Hiç komut bulunamadı. Oluşturmak için + tuşuna tıklayın.'),
    'del':                 (1076, 'Sil'),
    'name_required':       (1077, 'İsim gerekli'),
    'delete_q':            (1078, 'Silinsin mi?'),
    'delete_confirm':      (1079, '"{item_name}" öğesini silmek istediğinizden emin misiniz?\nBu işlem geri alınamaz.'),
    'dest_event':          (1080, 'Olay'),
    'dest_cmd':            (1081, 'Komut'),
    'commands_label':      (1082, 'Komut adını girin'),
    'unsaved_title':       (1083, 'Kaydedilmemiş değişiklikler'),
    'unsaved_body':        (1084, 'Bazı değişiklikler kaydedilmedi. Çıkmadan önce kaydetmek ister misiniz?'),
    'discard':             (1085, 'Yoksay'),
    'loading':             (1086, 'Yükleniyor...'),

    # ── wiki_view ─────────────────────────────────────────────
    'search_hint':          (1122, 'Bir fonksiyon ara...'),
    'check_updates':        (1123, 'Güncellemeleri kontrol et'),
    'checking':             (1124, 'Kontrol ediliyor...'),
    'downloading':          (1125, 'Wiki indiriliyor...'),
    'up_to_date':           (1126, 'Wiki güncel (v{v})'),
    'update_available':     (1127, 'Yeni güncelleme mevcut (v{v})'),
    'update_failed':        (1128, 'Güncelleme kontrolü başarısız oldu'),
    'no_cache':             (1129, 'Henüz yerel veri yok. "Güncellemeleri kontrol et"e basın.'),
    'no_results':           (1130, 'Sonuç yok'),
    'function_info':        (1131, 'Fonksiyon bilgisi'),
    'no_details':           (1132, 'Ayrıntı yok'),
    'open_dashboard':       (1133, 'Kontrol panelini aç'),
    'copy_syntax':          (1134, 'Kopyala'),
    'copied':               (1135, 'Kopyalandı!'),
    'syntax':               (1136, 'Sözdizimi'),
    'parameters':           (1137, 'Parametreler'),
    'example':              (1138, 'Örnek'),
    'notes':                (1139, 'Notlar'),
    'warnings':             (1140, 'Uyarılar'),
    'required':             (1141, 'Zorunlu'),
    'optional':             (1142, 'İsteğe bağlı'),
    'not_used_in_bot':      (1143, 'Bu fonksiyon bu botun komutlarında kullanılmıyor'),

    # ── wiki_view filters ─────────────────────────────────────
    'filter_all':           (1148, 'Tümü'),
    'filter_command':       (1149, 'Komut'),
    'filter_event':         (1150, 'Olay'),
    'filter_variable':      (1171, 'Değişkenler'),
    'filter_discord':       (1172, 'Discord'),
    'filter_time':          (1173, 'Zaman'),
    'filter_other':         (1174, 'Diğer'),
    'filter_title':         (1241, 'Kategoriler'),
    'filter_tooltip':       (1246, 'Filtrele'),
    'no_categories':        (1247, 'Henüz kategori yok'),

    # ── wiki_view callouts ────────────────────────────────────
    'callout_note':         (1144, 'Not'),
    'callout_limit':        (1145, 'Sınır'),
    'callout_important':    (1146, 'Bu önemli!'),
    'callout_question':     (1147, 'Bu nedir?'),

    # ── variables_view ────────────────────────────────────────
    'variables':            (1028, 'Değişkenler'),
    'variables_slash':      (1151, 'Değişken /'),
    'scoped_vars':          (1152, 'Kullanıcı başına değerler'),
    'value_label':          (1153, 'Değer'),
    'var_name_hint':        (1154, 'değişken_adı'),
    'var_value_hint':       (1155, 'değişken_değeri'),
    'info_var':             (1156, 'Değişken bilgisi'),
    'invalid_json':         (1157, 'Geçersiz JSON'),
    'json_must_be_object':  (1158, 'Üst düzey değer bir JSON nesnesi olmalıdır ({"userID": "value"}).'),
    'no_variables':         (1089, 'Değişken yok'),
    'enter_variable_name':  (1106, 'Değişken adını girin'),

    # ── App Updater ───────────────────────────────────────────
    'app_update_title':           (1159, 'Güncelleme mevcut'),
    'app_update_new_version':     (1160, 'Yeni sürüm'),
    'app_update_current_version': (1161, 'Mevcut'),
    'app_update_no_changelog':    (1162, 'Bu güncelleme için değişiklik günlüğü mevcut değil.'),
    'app_update_later':           (1163, 'Daha sonra'),
    'app_update_now':             (1164, 'Şimdi güncelle'),
    'app_update_downloading':     (1165, 'İndiriliyor'),
    'app_update_done':            (1166, 'İndirme tamamlandı ✓'),
    'app_update_failed':          (1167, 'İndirme başarısız oldu'),
    'app_update_open_installer':  (1168, 'Yükleyiciyi aç'),
    'app_update_installer_opened':(1169, 'Yükleyici açıldı. Kurulumu tamamlayın, ardından uygulamayı yeniden açın.'),
    'app_update_open_failed':     (1170, 'Yükleyici dosyası açılamadı'),

    # ── Status Bot View ───────────────────────────────────────
    'status_bot_section':         (1175, 'Bot durumu'),
    'status_bot_desc':            (1176, 'Botunuzun varlığını ve dönen durum mesajlarını yapılandırın'),
    'open_status_bot':            (1177, 'Durumu yönet'),
    'status_bot_title':           (1178, 'Durum botu'),
    'sv_status_label':            (1179, 'Durum'),
    'sv_loop_time_label':         (1180, 'Döngü süresi'),
    'sv_loop_time_seconds':       (1181, 'Saniye'),
    'sv_loop_time_hint':          (1182, 'Sadece tam sayı, en az 12 saniye'),
    'sv_activate_presence':       (1183, 'Bot varlığını etkinleştir'),
    'sv_status_entries':          (1184, 'Durum girdileri'),
    'sv_add_entry':               (1185, 'Yeni girdi ekle'),
    'sv_entry_details_ph':        (1186, 'Durum ayrıntıları'),
    'sv_status_online':           (1187, 'Çevrimiçi'),
    'sv_status_idle':             (1188, 'Boşta'),
    'sv_status_dnd':              (1189, 'Rahatsız Etmeyin'),
    'sv_status_invisible':        (1190, 'Görünmez'),
    'sv_create_edit_title':       (1191, 'Durum girdisi oluştur veya düzenle'),
    'sv_status_data':             (1192, 'Durum verisi'),
    'sv_prefix_status':           (1193, 'Durum öneki'),
    'sv_status_field':            (1194, 'Durum'),
    'sv_status_details':          (1195, 'Durum ayrıntıları'),
    'sv_prefix_hint':             (1196, 'Örneğin: oynuyor'),
    'sv_status_hint':             (1197, 'Kısa durum metni'),
    'sv_details_hint':            (1198, 'Durumun altında gösterilen ek ayrıntılar'),
    'sv_preview':                 (1199, 'Önizleme'),
    'sv_name_bot':                (1200, 'Bot adı'),
    'sv_app_badge':               (1201, 'Uygulama'),
    'sv_save_entry':              (1202, 'Girdiyi kaydet'),
    'sv_back':                    (1203, 'Geri'),
    'sv_no_entries':              (1204, 'Henüz durum girdisi yok.'),
    'sv_unit_second':             (1205, 'Saniye'),
    'sv_unit_minute':             (1206, 'Dakika'),
    'sv_unit_hour':               (1207, 'Saat'),
    'sv_unit_day':                (1208, 'Gün'),
    'sv_loop_time_integer_error': (1209, 'Sadece tam sayı — ondalık veya sembol yok'),
    'sv_loop_time_min_error':     (1210, 'Döngü süresi 12 saniyeden az olamaz'),
    'sv_activity_type':           (1211, 'Etkinlik türü'),
    'sv_activity_playing':        (1212, 'Oynuyor'),
    'sv_activity_streaming':      (1213, 'Yayın yapıyor'),
    'sv_activity_listening':      (1214, 'Dinliyor'),
    'sv_activity_watching':       (1215, 'İzliyor'),
    'sv_activity_competing':      (1216, 'Yarışıyor'),
    'sv_stream_url':              (1217, "Yayın URL'si"),
    'sv_stream_url_hint':         (1218, 'https://twitch.tv/... veya https://youtube.com/...'),
    'sv_stream_url_required':     (1219, "Yayın durumu için yayın URL'si gerekli"),
    'sv_stream_url_invalid':      (1220, 'Sadece Twitch veya YouTube bağlantılarına izin verilir'),
    'sv_help_note_title':         (1229, 'Notlar'),
    'sv_help_note_body':          (1230, 'Değişikliklerin uygulanması biraz zaman alır. Bot çalışırken bir durumu '
                                      'eklemek, düzenlemek veya silmek — ve varlığı açıp kapatmak — anında uygulanmaz. '
                                      'Bot önce mevcut listenin döngüsünü tamamlar, bu yüzden değişikliğinizin '
                                      'görünmesi biraz zaman alabilir.'),

    # ── Create Bot — Import from backup ────────────────────────────────────
    'import_zip_btn':           (1221, 'Yedekten geri yükle'),
    'import_zip_disabled_hint': (1222, 'Önce bot adını ve geçerli bir token belirleyin'),
    'import_zip_selected':      (1223, 'Yedek seçildi: {file_name}'),
    'import_zip_clear':         (1224, 'Kaldır'),
    'import_zip_invalid':       (1225, 'Bu bir bot yedek dosyası gibi görünmüyor'),
    'import_zip_pick_title':    (1226, 'Yedek ZIP dosyası seçin'),
    'import_zip_applied':       (1227, 'Bot oluşturuldu ve yedek geri yüklendi!'),
    'import_zip_failed':        (1228, 'Bot oluşturuldu, ancak yedek geri yüklenemedi'),

    # ── General Actions & Feedback ─────────────────────────────────────────
    'edit':                   (1094, 'Düzenle'),
    'delete':                 (1095, 'Sil'),
    'cancel':                 (1100, 'İptal'),
    'reset':                  (1242, 'Sıfırla'),
    'close':                  (1243, 'Kapat'),
    'done':                   (1244, 'Tamam'),
    'clear_search':           (1245, 'Aramayı temizle'),
    'saved_successfully':     (1231, 'Başarıyla kaydedildi'),

    # ── Mobile Warning ────────────────────────────────────────────────────
    'mobile_warn_title':      (1232, 'Mobil arka plan bildirimi'),
    'mobile_warn_body':       (1233, 'Mobil sistemlerde (sadece Android) bot çalıştırmak, işletim sisteminin katı '
                                      'arka plan kısıtlamalarına tabidir.\n\n'
                                      '• En iyi durumda, bot arka planda en fazla 6 saat çalışabilir.\n'
                                      '• Cihazınızın ayarlarında pil optimizasyonunu devre dışı bırakmanız gerekir '
                                      '("sınırsız" olarak ayarlayın).\n'
                                      '• Bazı cihazlar, uygulama küçültülür küçültülmez botu hemen askıya alabilir.\n\n'
                                      'Hosting/sunucu/VPS vb. üzerinde bot çalıştırma konusuna gelince, bu henüz '
                                      'desteklenmemektedir.'),

    # ── Command Editor Syntax Warning ─────────────────────────────────────
    'syntax_warn_banner':     (1234, 'Renk modu etkin. Büyük dosyalar için (2000 karakterden fazla), cihaz '
                                      'yavaşlamasını önlemek için renk modunu kapatın.'),
    'syntax_limit_refusal':   (1235, 'Renk modu etkinleştirilemiyor: performansı korumak için metin 2000 karakter '
                                      'sınırını aşıyor.'),
    'syntax_color_label':     (1236, 'Renk'),

    # ── Total Counts ──────────────────────────────────────────────────────
    'total_bots_count':       (1237, 'Sahip olduğunuz toplam bot sayısı: {count}'),
    'total_vars_count':       (1238, 'Toplam değişken: {count}'),
    'total_cmds_count':       (1239, 'Toplam komut: {count}'),
    'total_wiki_count':       (1240, 'Sonuçlar: {count}'),

    # ── Token Verification ────────────────────────────────────────────────
    'verify_token':           (1248, 'Tokeni doğrula'),
    'verifying':              (1249, 'Doğrulanıyor...'),
    'token_valid':            (1250, 'Bağlantı başarılı! Token geçerli.'),
    'token_invalid':          (1251, 'Geçersiz token veya bağlantı başarısız oldu.'),

    # ── Android Background Notification ────────────────────────────────────
    'fgs_state_working':          (1252, 'Bot çalışıyor | 🟢'),
    'server_status_online':       (1257, 'Sunucu çevrimiçi: {name}'),
    'server_status_stopped':      (1258, 'Sunucu durdu'),
    'fgs_limit_reached':          (1259, 'Android arka plan sınırına ulaşıldı (6 saat). Sunucuyu yeniden başlatmak '
                                      'için uygulamayı açın.'),
    'fgs_start_failed':           (1260, 'Arka plan servisi başlatılamadı: {error}'),
    'fgs_background_notice':      (1277, 'Bot arka planda çalışmaya devam eder. Uygulamayı son uygulamalar listesinden kaydırarak kapatmayın.'),
    'fgs_background_unprotected': (1278, 'Arka plan servisi başlatılamadı; bot durabilir. Uygulamayı açıp tekrar deneyin.'),
    'fgs_limit_warning':          (1279, 'Android arka plan sınırına yaklaşıldı. Botu çalışır durumda tutmak için uygulamayı açın.'),
    'fgs_alert_channel_name':     (1280, 'FDSB Bildirimleri'),
    'fgs_alert_channel_desc':     (1281, 'Bot arka plan durumu'),
    'fgs_default_title':          (1282, 'FDSB Bot Sunucusu'),

    # ── Privileged Gateway Intents Warning ────────────────────────────────
    'intents_warning_title':      (1261, "Ayrıcalıklı Intent'ler devre dışı"),
    'intents_warning_msg':        (1262, "Uyarı: Ayrıcalıklı ağ geçidi Intent'leri (varlık, üyeler, mesaj içeriği) "
                                      "Discord Geliştirici Portalı'nda etkinleştirilmemiş. Komutlar ve olaylar "
                                      "düzgün çalışmayabilir."),
    'open_dev_portal':            (1263, 'Portalda etkinleştir'),
    'intents_missing_msg':        (1276, "Uyarı: Aşağıdaki ayrıcalıklı ağ geçidi Intent'leri Discord Geliştirici Portalı'nda etkinleştirilmemiş:\n({missing})\nLütfen bunları Bot bölümünde etkinleştirin."),

    'syntax_switch_tooltip': (1264, 'Sözdizimi vurgulamayı aç/kapat'),
    'new_command_file':      (1265, 'yeni.fds'),
    'wiki_events_tooltip':   (1266, 'Wiki: Olaylar'),
    'new_variable_file':     (1267, 'yeni.json'),
    'scoped_json_title':     (1268, '{name} — kullanıcıya özel JSON verisi'),
    'avatar_change_title':   (1269, 'Bot Görselini Değiştir'),
    'avatar_change_body':    (1270, 'Botunuz için yeni bir görsel seçin. Bu görsel mevcut görselin yerini alacaktır.'),
    'avatar_choose_btn':     (1271, 'Görsel Seç'),
    'avatar_pick_title':     (1272, 'Bir görsel seçin'),
    'avatar_changed':        (1273, 'Bot görseli başarıyla güncellendi!'),
    'avatar_change_failed':  (1274, 'Bot görseli güncellenemedi'),
    'avatar_invalid_type':   (1275, 'Desteklenmeyen dosya. PNG, JPG, WEBP veya GIF görseli seçin.'),
}