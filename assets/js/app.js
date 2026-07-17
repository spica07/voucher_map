/* 서울 평생교육이용권 사용처 지도 — 앱 로직 */
(function () {
  'use strict';

  var VOUCHERS = window.VOUCHERS || [];
  var DATA_META = window.DATA_META || {};

  var KIND_SLUG = { '오프라인': 'offline', '온라인': 'online', '온/오프라인': 'mixed' };
  var KIND_COLOR = { '오프라인': '#5B4FE0', '온라인': '#22B8CF', '온/오프라인': '#F5A623' };
  var KIND_ORDER = ['오프라인', '온라인', '온/오프라인'];

  var CATEGORY_ORDER = ['학력보완교육', '성인 문해교육', '직업능력 향상교육',
    '성인 진로개발역량 향상교육', '인문교양교육', '문화예술교육', '시민참여교육'];

  var DISTRICT_ORDER = ['강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구',
    '금천구', '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구',
    '성동구', '성북구', '송파구', '양천구', '영등포구', '용산구', '은평구', '종로구', '중구', '중랑구'];

  var SEOUL_CENTER = [37.5514, 126.9910];
  var SEOUL_ZOOM = 11;

  var state = {
    q: '',
    district: '',
    kind: '',
    category: '',
    aiOnly: false,
    favOnly: false,
    view: 'list'
  };

  var favorites = loadFavorites();

  function loadFavorites() {
    try {
      return new Set(JSON.parse(localStorage.getItem('vm_favorites') || '[]'));
    } catch (e) { return new Set(); }
  }
  function saveFavorites() {
    localStorage.setItem('vm_favorites', JSON.stringify(Array.from(favorites)));
  }

  // 마지막으로 사용한 자치구 선택·빠른필터 버튼 상태를 이 기기에 기억한다
  function loadLastFilters() {
    try {
      return JSON.parse(localStorage.getItem('vm_lastFilters')) || null;
    } catch (e) { return null; }
  }
  function saveLastFilters() {
    try {
      var toggles = {};
      document.querySelectorAll('[data-toggle]').forEach(function (btn) {
        toggles[btn.getAttribute('data-toggle')] = !!state[btn.getAttribute('data-toggle')];
      });
      toggles.district = state.district;
      localStorage.setItem('vm_lastFilters', JSON.stringify(toggles));
    } catch (e) {}
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function safeUrl(u) {
    return /^https?:\/\//i.test(String(u == null ? '' : u)) ? String(u) : '';
  }

  function districtColor(d) {
    var idx = DISTRICT_ORDER.indexOf(d);
    if (idx === -1) return '#8D6E63';
    var hue = Math.round((idx * (360 / DISTRICT_ORDER.length)) % 360);
    return 'hsl(' + hue + ', 62%, 50%)';
  }
  function kindColor(k) { return KIND_COLOR[k] || '#8D6E63'; }
  function kindSlug(k) { return KIND_SLUG[k] || 'offline'; }

  /* ---------- 필터링 ---------- */
  function matches(f) {
    if (state.district && f.district !== state.district) return false;
    if (state.kind && f.kind !== state.kind) return false;
    if (state.category && f.categories.indexOf(state.category) === -1) return false;
    if (state.aiOnly && f.aiYn !== true) return false;
    if (state.favOnly && !favorites.has(f.id)) return false;
    if (state.q) {
      var q = state.q.toLowerCase();
      var hay = [f.name, f.address, f.district].join(' ').toLowerCase();
      if (hay.indexOf(q) === -1) return false;
    }
    return true;
  }

  /* ---------- 지도 ---------- */
  var map = L.map('map', { zoomControl: true, renderer: L.canvas() }).setView(SEOUL_CENTER, SEOUL_ZOOM);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
  var markerLayer = L.layerGroup().addTo(map);
  var markersById = {};

  function renderMarkers(list) {
    markerLayer.clearLayers();
    markersById = {};
    list.forEach(function (f) {
      if (f.lat == null || f.lng == null) return;
      var marker = L.circleMarker([f.lat, f.lng], {
        radius: 8,
        fillColor: kindColor(f.kind),
        color: '#ffffff',
        weight: 2,
        fillOpacity: 0.9
      });
      if (f.geoApprox) marker.setStyle({ fillOpacity: 0.45, dashArray: '2,3' });
      var popupHtml =
        '<div class="popup-name">' + esc(f.name) + '</div>' +
        '<div class="popup-meta">' + esc(f.district) + ' · ' + esc(f.kind) +
        (f.aiYn === true ? ' · AI·디지털' : '') +
        (f.geoApprox ? ' · <span class="approx-note">위치 확인 필요</span>' : '') + '</div>' +
        '<button class="popup-btn" data-popup-detail="' + f.id + '">자세히 보기</button>';
      marker.bindPopup(popupHtml);
      marker.addTo(markerLayer);
      markersById[f.id] = marker;
    });
  }

  /* ---------- 카드에서 지도 위치로 이동 ---------- */
  function locateOnMap(id) {
    var f = VOUCHERS.find(function (x) { return x.id === id; });
    if (!f || f.lat == null || f.lng == null) return;
    if (window.innerWidth <= 900 && state.view !== 'map') {
      state.view = 'map';
      document.querySelectorAll('#viewToggle .pill').forEach(function (p) {
        p.classList.toggle('active', p.getAttribute('data-view') === 'map');
      });
      var grid = document.querySelector('.content-grid');
      grid.classList.remove('view-list');
      grid.classList.add('view-map');
      setTimeout(function () { map.invalidateSize(); }, 50);
    }
    map.flyTo([f.lat, f.lng], 16, { duration: 0.8 });
    var marker = markersById[f.id];
    if (marker) map.once('moveend', function () { marker.openPopup(); });
  }

  /* ---------- 카드 ---------- */
  function cardHtml(f) {
    var dc = districtColor(f.district);
    var fav = favorites.has(f.id);
    var tags = [
      '<span class="tag district" style="background:' + dc + '">' + esc(f.district) + '</span>',
      '<span class="tag kind-' + kindSlug(f.kind) + '">' + esc(f.kind) + '</span>'
    ];
    if (f.aiYn === true) tags.push('<span class="tag ai">AI·디지털</span>');
    if (f.geoApprox) tags.push('<span class="tag approx">위치 확인 필요</span>');
    var info = [];
    info.push('<div class="card-info">' +
      (f.address ? esc(f.address) : '온라인 서비스(별도 방문지 없음)') + '</div>');
    if (f.categories.length) {
      info.push('<div class="card-info">' + esc(f.categories.join(', ')) + '</div>');
    }
    return (
      '<article class="facility-card" data-id="' + f.id + '">' +
        '<div class="card-body">' +
          '<div class="card-title-row">' +
            '<h3 class="card-name">' + esc(f.name) + '</h3>' +
            '<button class="fav-btn" data-fav="' + f.id + '" aria-label="찜">' + (fav ? '❤️' : '🤍') + '</button>' +
          '</div>' +
          '<div class="card-tags">' + tags.join('') + '</div>' +
          info.join('') +
          (f.lat != null ? '<button class="card-locate" data-locate="' + f.id + '">위치보기</button>' : '') +
        '</div>' +
      '</article>'
    );
  }

  function renderCards(list) {
    var grid = document.getElementById('cardGrid');
    grid.innerHTML = list.map(cardHtml).join('');
    document.getElementById('emptyState').hidden = list.length > 0;
  }

  /* ---------- 상세 모달 ---------- */
  function detailRow(k, v, isLink) {
    if (!v) return '';
    var val = isLink
      ? (safeUrl(v) ? '<a href="' + esc(safeUrl(v)) + '" target="_blank" rel="noopener">' + esc(v) + '</a>' : esc(v))
      : esc(v);
    return '<div class="detail-item"><span class="k">' + k + '</span><span class="v">' + val + '</span></div>';
  }

  window.openFacilityModal = function (id) {
    var f = VOUCHERS.find(function (x) { return x.id === id; });
    if (!f) return;
    var dc = districtColor(f.district);
    var fav = favorites.has(f.id);
    var naverUrl = f.address
      ? 'https://map.naver.com/p/search/' + encodeURIComponent(f.address)
      : '';
    var body = document.getElementById('modalBody');
    body.innerHTML =
      '<h2 class="modal-title">' + esc(f.name) + '</h2>' +
      '<div class="modal-tags">' +
        '<span class="tag district" style="background:' + dc + '">' + esc(f.district) + '</span>' +
        '<span class="tag kind-' + kindSlug(f.kind) + '">' + esc(f.kind) + '</span>' +
        (f.aiYn === true ? '<span class="tag ai">AI·디지털이용권</span>' : '') +
        (f.geoApprox ? '<span class="tag approx">위치 확인 필요</span>' : '') +
      '</div>' +
      (f.geoApprox
        ? '<p class="modal-intro">정확한 건물 위치를 찾지 못해 자치구 중심 부근에 표시했어요. 실제 위치는 주소를 참고해 주세요.</p>'
        : '') +
      '<div class="detail-list">' +
        detailRow('주소', f.address || '온라인 서비스(별도 방문지 없음)') +
        detailRow('분야', f.categories.join(', ')) +
        detailRow('전화', f.phone) +
        detailRow('자료 기준일', DATA_META.surveyDate) +
      '</div>' +
      '<div class="modal-links">' +
        (naverUrl ? '<a class="link-btn map" href="' + naverUrl + '" target="_blank" rel="noopener">네이버 길찾기</a>' : '') +
        (safeUrl(f.homepage) ? '<a class="link-btn web" href="' + esc(safeUrl(f.homepage)) + '" target="_blank" rel="noopener">홈페이지</a>' : '') +
        '<button class="link-btn fav" data-fav="' + f.id + '">' + (fav ? '찜 해제' : '찜하기') + '</button>' +
      '</div>';
    document.getElementById('modalOverlay').hidden = false;
    document.body.style.overflow = 'hidden';
  };

  function closeModal() {
    document.getElementById('modalOverlay').hidden = true;
    document.body.style.overflow = '';
  }

  /* ---------- 렌더 파이프라인 ---------- */
  function render() {
    var list = VOUCHERS.filter(matches);
    renderMarkers(list);
    renderCards(list);
    document.getElementById('resultCount').textContent =
      '총 ' + list.length + '곳' + (list.length < VOUCHERS.length ? ' (전체 ' + VOUCHERS.length + '곳 중)' : '');
  }

  /* ---------- 초기 UI 구성 ---------- */
  function buildFilterPills() {
    var kindRow = document.getElementById('kindFilters');
    var presentK = {};
    VOUCHERS.forEach(function (f) { presentK[f.kind] = true; });
    var kPills = ['<button class="pill active" data-kind="">전체</button>'];
    KIND_ORDER.forEach(function (k) {
      if (presentK[k]) kPills.push('<button class="pill" data-kind="' + esc(k) + '">' + esc(k) + '</button>');
    });
    kindRow.insertAdjacentHTML('beforeend', kPills.join(''));

    var catRow = document.getElementById('categoryFilters');
    var presentC = {};
    VOUCHERS.forEach(function (f) { f.categories.forEach(function (c) { presentC[c] = true; }); });
    var cPills = ['<button class="pill active" data-category="">전체</button>'];
    CATEGORY_ORDER.forEach(function (c) {
      if (presentC[c]) cPills.push('<button class="pill" data-category="' + esc(c) + '">' + esc(c) + '</button>');
    });
    catRow.insertAdjacentHTML('beforeend', cPills.join(''));
  }

  function buildDistrictSelect() {
    var sel = document.getElementById('districtSelect');
    var counts = {};
    VOUCHERS.forEach(function (f) { counts[f.district] = (counts[f.district] || 0) + 1; });
    DISTRICT_ORDER.forEach(function (d) {
      if (!counts[d]) return;
      var opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d + ' (' + counts[d] + ')';
      sel.appendChild(opt);
    });
  }

  function buildLegend() {
    document.getElementById('mapLegend').innerHTML = KIND_ORDER.map(function (k) {
      return '<span><span class="legend-dot" style="background:' + KIND_COLOR[k] + '"></span>' + k + '</span>';
    }).join('');
  }

  /* ---------- 이벤트 ---------- */
  function setDistrict(d) {
    state.district = d;
    document.getElementById('districtSelect').value = d;
    if (d) {
      var sub = VOUCHERS.filter(function (f) { return f.district === d && f.lat != null; });
      if (sub.length) {
        var lat = sub.reduce(function (s, f) { return s + f.lat; }, 0) / sub.length;
        var lng = sub.reduce(function (s, f) { return s + f.lng; }, 0) / sub.length;
        map.flyTo([lat, lng], 14, { duration: 0.8 });
      }
    } else {
      map.flyTo(SEOUL_CENTER, SEOUL_ZOOM, { duration: 0.8 });
    }
    saveLastFilters();
    render();
  }

  var searchTimer = null;
  document.getElementById('searchInput').addEventListener('input', function (e) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      state.q = e.target.value.trim();
      render();
    }, 200);
  });

  document.getElementById('districtSelect').addEventListener('change', function (e) {
    setDistrict(e.target.value);
  });

  var filterToggleBtn = document.getElementById('filterToggleBtn');
  var filterGroups = document.getElementById('filterGroups');
  filterToggleBtn.addEventListener('click', function () {
    var willOpen = filterGroups.hidden;
    filterGroups.hidden = !willOpen;
    filterToggleBtn.textContent = willOpen ? '▲' : '▼';
    var label = willOpen ? '필터 닫기' : '필터 열기';
    filterToggleBtn.title = label;
    filterToggleBtn.setAttribute('aria-label', label);
    filterToggleBtn.setAttribute('aria-expanded', String(willOpen));
  });

  document.addEventListener('click', function (e) {
    var t = e.target;

    var favBtn = t.closest('[data-fav]');
    if (favBtn) {
      e.stopPropagation();
      var id = Number(favBtn.getAttribute('data-fav'));
      if (favorites.has(id)) favorites.delete(id); else favorites.add(id);
      saveFavorites();
      render();
      if (!document.getElementById('modalOverlay').hidden) window.openFacilityModal(id);
      return;
    }

    var locateBtn = t.closest('[data-locate]');
    if (locateBtn) {
      e.stopPropagation();
      locateOnMap(Number(locateBtn.getAttribute('data-locate')));
      return;
    }

    var popupBtn = t.closest('[data-popup-detail]');
    if (popupBtn) {
      window.openFacilityModal(Number(popupBtn.getAttribute('data-popup-detail')));
      return;
    }

    var kindPill = t.closest('[data-kind]');
    if (kindPill) {
      state.kind = kindPill.getAttribute('data-kind');
      document.querySelectorAll('#kindFilters .pill').forEach(function (p) {
        p.classList.toggle('active', p === kindPill);
      });
      render();
      return;
    }

    var catPill = t.closest('[data-category]');
    if (catPill) {
      state.category = catPill.getAttribute('data-category');
      document.querySelectorAll('#categoryFilters .pill').forEach(function (p) {
        p.classList.toggle('active', p === catPill);
      });
      render();
      return;
    }

    var togglePill = t.closest('[data-toggle]');
    if (togglePill) {
      var key = togglePill.getAttribute('data-toggle');
      state[key] = !state[key];
      togglePill.classList.toggle('active', state[key]);
      saveLastFilters();
      render();
      return;
    }

    var viewBtn = t.closest('[data-view]');
    if (viewBtn) {
      state.view = viewBtn.getAttribute('data-view');
      document.querySelectorAll('#viewToggle .pill').forEach(function (p) {
        p.classList.toggle('active', p === viewBtn);
      });
      var grid = document.querySelector('.content-grid');
      grid.classList.remove('view-map', 'view-list');
      grid.classList.add('view-' + state.view);
      if (state.view === 'map') setTimeout(function () { map.invalidateSize(); }, 50);
      return;
    }

    var card = t.closest('.facility-card');
    if (card) {
      window.openFacilityModal(Number(card.getAttribute('data-id')));
      return;
    }

    if (t.id === 'modalClose' || t.id === 'modalOverlay') closeModal();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  document.getElementById('resetBtn').addEventListener('click', function () {
    state.q = ''; state.kind = ''; state.category = '';
    state.aiOnly = false; state.favOnly = false;
    document.getElementById('searchInput').value = '';
    document.querySelectorAll('.filter-bar .pill').forEach(function (p) {
      p.classList.toggle('active',
        p.getAttribute('data-kind') === '' || p.getAttribute('data-category') === '');
    });
    document.querySelectorAll('[data-toggle]').forEach(function (p) { p.classList.remove('active'); });
    setDistrict('');
  });

  /* ---------- 시작 ---------- */
  document.getElementById('surveyDate').textContent = DATA_META.surveyDate || '';
  buildFilterPills();
  buildDistrictSelect();
  buildLegend();
  // 모바일 기본은 목록 뷰
  if (window.innerWidth <= 900) {
    document.querySelector('.content-grid').classList.add('view-list');
  }
  // 리포트 등에서 ?district=자치구 로 진입한 경우 URL을 우선 적용,
  // 그렇지 않으면 이 기기에 마지막으로 저장된 필터를 복원한다
  var params = new URLSearchParams(location.search);
  var paramDistrict = params.get('district');
  if (paramDistrict && DISTRICT_ORDER.indexOf(paramDistrict) !== -1) {
    setDistrict(paramDistrict);
  } else {
    var savedFilters = loadLastFilters();
    if (savedFilters) {
      document.querySelectorAll('[data-toggle]').forEach(function (btn) {
        var key = btn.getAttribute('data-toggle');
        if (savedFilters[key]) {
          state[key] = true;
          btn.classList.add('active');
        }
      });
      if (savedFilters.district && DISTRICT_ORDER.indexOf(savedFilters.district) !== -1) {
        setDistrict(savedFilters.district);
      } else {
        render();
      }
    } else {
      render();
    }
  }

  // PWA: 서비스 워커 등록 (홈 화면 설치 · 오프라인 지원)
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('sw.js').catch(function (err) {
        console.warn('서비스 워커 등록 실패:', err);
      });
    });
  }
})();
