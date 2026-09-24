import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addFoodPhoto,
  createFood,
  deleteFood,
  deleteFoodPhoto,
  fetchFoods,
  type Food,
  type FoodIn,
  type PhotoKind,
  readLabel,
  updateFood,
} from '../api/foods';

/** A photo still to send with the sheet. */
export interface NewPhoto {
  file: File;
  kind: PhotoKind;
}

export const useFoods = () =>
  useQuery({ queryKey: ['foods'], queryFn: fetchFoods });

function useFoodAction<A, R>(fn: (arg: A) => Promise<R>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => client.invalidateQueries({ queryKey: ['foods'] }),
  });
}

/** Save the sheet (new or changed), then its new photos one by one. */
async function save(args: {
  id?: string;
  body: FoodIn;
  photos: NewPhoto[];
}): Promise<Food> {
  let food = args.id
    ? await updateFood(args.id, args.body)
    : await createFood(args.body);
  for (const photo of args.photos) {
    food = await addFoodPhoto(food.id, photo.file, photo.kind);
  }
  return food;
}

export const useSaveFood = () => useFoodAction(save);
export const useDeleteFood = () => useFoodAction(deleteFood);
export const useDeleteFoodPhoto = () =>
  useFoodAction((a: { id: string; photoId: string }) =>
    deleteFoodPhoto(a.id, a.photoId),
  );
export const useReadLabel = () => useMutation({ mutationFn: readLabel });
