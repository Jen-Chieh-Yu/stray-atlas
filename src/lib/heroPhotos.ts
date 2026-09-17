/** Photos for the home page hero. Illustrative only: none of these animals
 *  is in a Taiwanese shelter, and the page says so on every slide.
 *
 *  All are free to use under the Unsplash License
 *  (https://unsplash.com/license), checked on each photo page on
 *  2026-09-17. The WebP files are made by scripts/build_hero.py from
 *  originals kept out of git; the slugs there must match these ids.
 *
 *  `focus` is the object-position that keeps the animals' faces inside the
 *  wide desktop crop.
 *
 *  Used by: HeroCarousel.vue (the slides and their credit line) and
 *  AboutView.vue (the photo credits). */
import catDogGrass960 from '@/assets/hero/cat-dog-grass-960.webp'
import catDogGrass1920 from '@/assets/hero/cat-dog-grass-1920.webp'
import dogWall960 from '@/assets/hero/dog-wall-960.webp'
import dogWall1920 from '@/assets/hero/dog-wall-1920.webp'
import catPavement960 from '@/assets/hero/cat-pavement-960.webp'
import catPavement1920 from '@/assets/hero/cat-pavement-1920.webp'
import catDogSidewalk960 from '@/assets/hero/cat-dog-sidewalk-960.webp'
import catDogSidewalk1920 from '@/assets/hero/cat-dog-sidewalk-1920.webp'
import dogsDirtRoad960 from '@/assets/hero/dogs-dirt-road-960.webp'
import dogsDirtRoad1920 from '@/assets/hero/dogs-dirt-road-1920.webp'
import catTabby960 from '@/assets/hero/cat-tabby-960.webp'
import catTabby1920 from '@/assets/hero/cat-tabby-1920.webp'
import catDogDoorway960 from '@/assets/hero/cat-dog-doorway-960.webp'
import catDogDoorway1920 from '@/assets/hero/cat-dog-doorway-1920.webp'
import catDogsSnow960 from '@/assets/hero/cat-dogs-snow-960.webp'
import catDogsSnow1920 from '@/assets/hero/cat-dogs-snow-1920.webp'

export interface HeroPhoto {
  id: string
  small: string
  large: string
  alt: string
  focus: string
  photographer: string
  /** The photo's page on Unsplash, which also credits the photographer. */
  url: string
}

export const HERO_PHOTOS: HeroPhoto[] = [
  {
    id: 'cat-dog-grass',
    small: catDogGrass960,
    large: catDogGrass1920,
    alt: '一隻虎斑貓和一隻黑白幼犬趴在草地上',
    focus: '50% 22%',
    photographer: 'Andrew S',
    url: 'https://unsplash.com/photos/a-dog-and-a-cat-laying-in-the-grass-ouo1hbizWwo',
  },
  {
    id: 'dog-wall',
    small: dogWall960,
    large: dogWall1920,
    alt: '一隻棕白色短毛狗坐在石牆前',
    focus: '50% 8%',
    photographer: 'Catarina Carvalho',
    url: 'https://unsplash.com/photos/short-coat-brown-and-white-dog-sitting-near-gray-concrete-wall-during-daytime-1K7Qf8OBXjU',
  },
  {
    id: 'cat-pavement',
    small: catPavement960,
    large: catPavement1920,
    alt: '一隻橘色虎斑貓坐在石板路上',
    focus: '50% 30%',
    photographer: 'Akira',
    url: 'https://unsplash.com/photos/orange-tabby-cat-sitting-on-gray-concrete-floor-ajs8oiV3CfM',
  },
  {
    id: 'cat-dog-sidewalk',
    small: catDogSidewalk960,
    large: catDogSidewalk1920,
    alt: '一隻虎斑貓和一隻黑棕色幼犬坐在人行道上',
    focus: '50% 55%',
    photographer: 'nygi',
    url: 'https://unsplash.com/photos/a-cat-and-a-dog-sitting-on-the-sidewalk-88B-uqWmk4A',
  },
  {
    id: 'dogs-dirt-road',
    small: dogsDirtRoad960,
    large: dogsDirtRoad1920,
    alt: '兩隻小型犬在泥土路上奔跑',
    focus: '50% 20%',
    photographer: 'Alvan Nee',
    url: 'https://unsplash.com/photos/two-brown-and-white-dogs-running-dirt-road-during-daytime-T-0EW-SEbsE',
  },
  {
    id: 'cat-tabby',
    small: catTabby960,
    large: catTabby1920,
    alt: '一隻灰色虎斑幼貓坐在暗處',
    focus: '50% 25%',
    photographer: 'Ricardo IV Tamayo',
    url: 'https://unsplash.com/photos/gray-tabby-cat-on-gray-surface-dwS880MZe3k',
  },
  {
    id: 'cat-dog-doorway',
    small: catDogDoorway960,
    large: catDogDoorway1920,
    alt: '一隻虎斑貓趴在睡著的黃狗身上',
    focus: '50% 32%',
    photographer: 'Glomad Marketing',
    url: 'https://unsplash.com/photos/gray-cat-sitting-on-lying-brown-dog-6VQlKJp2vpo',
  },
  {
    id: 'cat-dogs-snow',
    small: catDogsSnow960,
    large: catDogsSnow1920,
    alt: '一隻橘貓和兩隻博美犬在雪地上',
    focus: '50% 35%',
    photographer: 'Daniel Tuttle',
    url: 'https://unsplash.com/photos/brown-cat-beside-dog-during-daytime-khAuelKVnRg',
  },
]
